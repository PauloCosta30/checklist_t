"""
🛒 Scraper — Amazon Brasil
   Busca produtos com erro de preço via scraping HTML
"""

import asyncio
import hashlib
import logging
import random
import re
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup

from config import Config

logger = logging.getLogger("Amazon-Scraper")

AMAZON_SEARCH_URL = "https://www.amazon.com.br/s"


def _preco_para_float(texto: str) -> float:
    """Converte 'R$ 1.299,99' para 1299.99"""
    try:
        limpo = re.sub(r"[^\d,]", "", texto)
        limpo = limpo.replace(",", ".")
        # Se tiver mais de um ponto (ex: 1.299.99), tratar
        partes = limpo.split(".")
        if len(partes) > 2:
            limpo = "".join(partes[:-1]) + "." + partes[-1]
        return float(limpo)
    except Exception:
        return 0.0


async def scrape_amazon(keyword: str, preco_max: int) -> List[dict]:
    """
    Busca produtos na Amazon Brasil via scraping.
    Retorna lista de produtos que parecem erro de preço.
    """
    produtos = []

    params = {
        "k": keyword,
        "rh": f"p_36:0-{preco_max * 100}",  # em centavos
        "s": "price-asc-rank",
        "language": "pt_BR",
    }

    headers = {
        "User-Agent": random.choice(Config.USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                AMAZON_SEARCH_URL,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT),
                ssl=False,
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Amazon retornou {resp.status} para '{keyword}'")
                    return []

                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                items = soup.select('[data-component-type="s-search-result"]')

                for item in items[:10]:  # top 10 resultados
                    produto = _processar_item_amazon(item, keyword)
                    if produto:
                        produtos.append(produto)

    except asyncio.TimeoutError:
        logger.warning(f"Timeout na Amazon para '{keyword}'")
    except Exception as e:
        logger.error(f"Erro Amazon scraper '{keyword}': {e}")

    return produtos


def _processar_item_amazon(item, keyword: str) -> Optional[dict]:
    """Processa um item da Amazon e verifica se é erro de preço"""
    try:
        # Nome do produto
        nome_el = item.select_one("h2 a span")
        if not nome_el:
            return None
        nome = nome_el.get_text(strip=True)

        # Link
        link_el = item.select_one("h2 a")
        link = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            link = f"https://www.amazon.com.br{href}" if href.startswith("/") else href

        # Preço atual
        preco_el = item.select_one(".a-price .a-offscreen")
        if not preco_el:
            return None
        preco = _preco_para_float(preco_el.get_text(strip=True))
        if preco <= 0:
            return None

        # Preço original (riscado)
        preco_original = preco
        preco_orig_el = item.select_one(".a-price.a-text-price .a-offscreen")
        if preco_orig_el:
            preco_original = _preco_para_float(preco_orig_el.get_text(strip=True))

        # Desconto em badge (ex: "-65%")
        badge_el = item.select_one(".a-badge-text, .savingsPercentage")
        desconto_pct = 0.0

        if badge_el:
            badge_txt = badge_el.get_text(strip=True)
            match = re.search(r"(\d+)", badge_txt)
            if match:
                desconto_pct = float(match.group(1))

        # Calcular desconto por preços se não veio em badge
        if desconto_pct == 0 and preco_original > preco:
            desconto_pct = ((preco_original - preco) / preco_original) * 100

        if desconto_pct <= 0:
            return None

        # ID único
        prod_id = hashlib.md5(f"amz_{link}_{preco}".encode()).hexdigest()

        return {
            "id": prod_id,
            "nome": nome,
            "preco": preco,
            "preco_original": preco_original if preco_original > preco else preco * 1.5,
            "desconto_pct": desconto_pct,
            "loja": "Amazon Brasil",
            "link": link,
            "keyword": keyword,
        }

    except Exception as e:
        logger.debug(f"Erro ao processar item Amazon: {e}")
        return None
