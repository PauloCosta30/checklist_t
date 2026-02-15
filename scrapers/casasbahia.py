"""
🛒 Scraper — Casas Bahia
   Busca produtos via scraping HTML com headers reais
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

logger = logging.getLogger("CasasBahia-Scraper")


def _headers_cb() -> dict:
    return {
        "User-Agent": random.choice(Config.USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }


def _parse_preco(texto: str) -> float:
    try:
        limpo = re.sub(r"[^\d,]", "", texto).strip()
        if not limpo:
            return 0.0
        limpo = limpo.replace(",", ".")
        partes = limpo.split(".")
        if len(partes) > 2:
            limpo = "".join(partes[:-1]) + "." + partes[-1]
        return float(limpo)
    except Exception:
        return 0.0


async def scrape_casasbahia(keyword: str, preco_max: int) -> List[dict]:
    """Busca produtos na Casas Bahia via scraping HTML."""
    produtos = []

    slug = keyword.replace(" ", "%20")
    url = f"https://www.casasbahia.com.br/busca/{slug}?ordenar=menorpreco"

    for tentativa in range(2):
        try:
            await asyncio.sleep(random.uniform(1.0, 2.5))

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=_headers_cb(),
                    timeout=aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT),
                    ssl=False,
                    allow_redirects=True,
                ) as resp:
                    if resp.status == 403:
                        logger.warning(f"Casas Bahia bloqueou (403) para '{keyword}' — tentativa {tentativa+1}")
                        await asyncio.sleep(3 + tentativa * 2)
                        continue
                    if resp.status != 200:
                        logger.warning(f"Casas Bahia retornou {resp.status} para '{keyword}'")
                        return []

                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Seletores do layout atual da CB
                    cards = (
                        soup.select('[data-testid="product-card"]')
                        or soup.select(".product-card")
                        or soup.select('[class*="ProductCard"]')
                        or soup.select("article")
                    )

                    for card in cards[:15]:
                        produto = _processar_card(card, keyword, preco_max)
                        if produto:
                            produtos.append(produto)

                    if produtos:
                        break

        except asyncio.TimeoutError:
            logger.warning(f"Timeout Casas Bahia '{keyword}'")
            break
        except Exception as e:
            logger.error(f"Erro Casas Bahia '{keyword}': {e}")
            break

    return produtos


def _processar_card(card, keyword: str, preco_max: int) -> Optional[dict]:
    try:
        # Nome
        nome_el = (
            card.select_one('[data-testid="product-card-name"]')
            or card.select_one("h2")
            or card.select_one("h3")
            or card.select_one('[class*="ProductTitle"]')
            or card.select_one('[class*="product-title"]')
        )
        nome = nome_el.get_text(strip=True) if nome_el else ""
        if not nome:
            return None

        # Preço atual
        preco_el = (
            card.select_one('[data-testid="product-card-selling-price"]')
            or card.select_one('[class*="SalePrice"]')
            or card.select_one('[class*="sale-price"]')
            or card.select_one('[class*="price-final"]')
        )
        if not preco_el:
            return None
        preco = _parse_preco(preco_el.get_text(strip=True))
        if preco <= 0 or preco > preco_max:
            return None

        # Preço original
        orig_el = (
            card.select_one('[data-testid="product-card-original-price"]')
            or card.select_one('[class*="RegularPrice"]')
            or card.select_one('[class*="regular-price"]')
            or card.select_one("s")
            or card.select_one("del")
        )
        preco_original = _parse_preco(orig_el.get_text(strip=True)) if orig_el else 0.0

        desconto_pct = 0.0
        if preco_original > preco:
            desconto_pct = ((preco_original - preco) / preco_original) * 100

        # Link
        link_el = card.select_one("a")
        link = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            link = href if href.startswith("http") else f"https://www.casasbahia.com.br{href}"

        prod_id = hashlib.md5(f"cb_{link}_{preco}".encode()).hexdigest()

        return {
            "id": prod_id,
            "nome": nome,
            "preco": preco,
            "preco_original": preco_original,
            "desconto_pct": desconto_pct,
            "loja": "Casas Bahia",
            "link": link,
            "keyword": keyword,
        }

    except Exception as e:
        logger.debug(f"Erro ao processar card CB: {e}")
        return None
