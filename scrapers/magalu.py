"""
🛒 Scraper — Magazine Luiza (Magalu)
   Busca produtos via API de busca do Magalu
"""

import asyncio
import hashlib
import logging
import random
import re
from typing import List, Optional

import aiohttp

from config import Config

logger = logging.getLogger("Magalu-Scraper")

MAGALU_API_URL = "https://www.magazineluiza.com.br/busca/{query}/"


async def scrape_magalu(keyword: str, preco_max: int) -> List[dict]:
    """Busca produtos no Magalu via API de search."""
    produtos = []

    # Magalu tem uma API de busca paginada
    api_url = "https://www.magazineluiza.com.br/api/luizalabs/browse/v1/search/"

    params = {
        "q": keyword,
        "page": 1,
        "page_size": 20,
        "sort": "price:asc",
    }

    headers = {
        "User-Agent": random.choice(Config.USER_AGENTS),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Referer": f"https://www.magazineluiza.com.br/busca/{keyword.replace(' ', '%20')}/",
        "Origin": "https://www.magazineluiza.com.br",
        "x-api-key": "dGVzdGU=",  # header esperado pela API pública
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                api_url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT),
                ssl=False,
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Magalu retornou {resp.status} para '{keyword}', tentando fallback HTML...")
                    return await _scrape_magalu_html(keyword, preco_max)

                data = await resp.json(content_type=None)
                items = (
                    data.get("products", [])
                    or data.get("results", [])
                    or data.get("data", {}).get("products", [])
                )

                for item in items[:15]:
                    produto = _processar_item_magalu(item, keyword, preco_max)
                    if produto:
                        produtos.append(produto)

    except asyncio.TimeoutError:
        logger.warning(f"Timeout no Magalu para '{keyword}'")
    except Exception as e:
        logger.error(f"Erro Magalu scraper '{keyword}': {e}")
        try:
            return await _scrape_magalu_html(keyword, preco_max)
        except Exception:
            pass

    return produtos


async def _scrape_magalu_html(keyword: str, preco_max: int) -> List[dict]:
    """Fallback: scraping HTML da página de busca do Magalu"""
    from bs4 import BeautifulSoup
    produtos = []

    url = f"https://www.magazineluiza.com.br/busca/{keyword.replace(' ', '%20')}/?from=submit&page=1"

    headers = {
        "User-Agent": random.choice(Config.USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT),
                ssl=False,
            ) as resp:
                if resp.status != 200:
                    return []

                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                # Magalu usa data-testid nos cards de produto
                cards = soup.select('[data-testid="product-card-container"]')
                if not cards:
                    cards = soup.select("li[data-testid]")

                for card in cards[:15]:
                    produto = _processar_card_html_magalu(card, keyword, preco_max)
                    if produto:
                        produtos.append(produto)

    except Exception as e:
        logger.error(f"Erro Magalu HTML fallback '{keyword}': {e}")

    return produtos


def _processar_item_magalu(item: dict, keyword: str, preco_max: int) -> Optional[dict]:
    try:
        nome = item.get("title") or item.get("name") or item.get("description", "")
        if not nome:
            return None

        # Preço
        preco = float(
            item.get("price")
            or item.get("sale_price")
            or item.get("best_price")
            or 0
        )
        if preco <= 0 or preco > preco_max:
            return None

        # Preço original
        preco_original = float(
            item.get("original_price")
            or item.get("list_price")
            or item.get("regular_price")
            or 0
        )

        desconto_pct = 0.0
        if preco_original > preco:
            desconto_pct = ((preco_original - preco) / preco_original) * 100

        # Link
        slug = item.get("url") or item.get("slug") or item.get("id", "")
        link = (
            slug if str(slug).startswith("http")
            else f"https://www.magazineluiza.com.br{slug}"
        )

        prod_id = hashlib.md5(f"mg_{item.get('id','')}_{preco}".encode()).hexdigest()

        return {
            "id": prod_id,
            "nome": nome,
            "preco": preco,
            "preco_original": preco_original,
            "desconto_pct": desconto_pct,
            "loja": "Magazine Luiza",
            "link": link,
            "keyword": keyword,
        }

    except Exception as e:
        logger.debug(f"Erro ao processar item Magalu: {e}")
        return None


def _processar_card_html_magalu(card, keyword: str, preco_max: int) -> Optional[dict]:
    try:
        # Nome
        nome_el = card.select_one('[data-testid="product-title"], h2, .product-title')
        nome = nome_el.get_text(strip=True) if nome_el else ""
        if not nome:
            return None

        # Preço atual
        preco_el = card.select_one('[data-testid="price-value"], .price-template__text')
        if not preco_el:
            return None
        preco_txt = preco_el.get_text(strip=True)
        preco = _parse_preco_br(preco_txt)
        if preco <= 0 or preco > preco_max:
            return None

        # Preço original
        orig_el = card.select_one('[data-testid="original-price"], .price-template__original-price')
        preco_original = _parse_preco_br(orig_el.get_text(strip=True)) if orig_el else 0.0

        desconto_pct = 0.0
        if preco_original > preco:
            desconto_pct = ((preco_original - preco) / preco_original) * 100

        # Link
        link_el = card.select_one("a")
        link = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            link = href if href.startswith("http") else f"https://www.magazineluiza.com.br{href}"

        prod_id = hashlib.md5(f"mg_html_{link}_{preco}".encode()).hexdigest()

        return {
            "id": prod_id,
            "nome": nome,
            "preco": preco,
            "preco_original": preco_original,
            "desconto_pct": desconto_pct,
            "loja": "Magazine Luiza",
            "link": link,
            "keyword": keyword,
        }

    except Exception as e:
        logger.debug(f"Erro ao processar card HTML Magalu: {e}")
        return None


def _parse_preco_br(texto: str) -> float:
    """Converte 'R$ 1.299,99' para 1299.99"""
    try:
        limpo = re.sub(r"[^\d,]", "", texto).replace(",", ".")
        partes = limpo.split(".")
        if len(partes) > 2:
            limpo = "".join(partes[:-1]) + "." + partes[-1]
        return float(limpo)
    except Exception:
        return 0.0
