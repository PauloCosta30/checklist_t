"""
🛒 Scraper — Casas Bahia
   Busca produtos via API interna do site
"""

import asyncio
import hashlib
import logging
import random
import re
from typing import List, Optional

import aiohttp

from config import Config

logger = logging.getLogger("CasasBahia-Scraper")

CB_API_URL = "https://www.casasbahia.com.br/api/bff/search/v1/search"


async def scrape_casasbahia(keyword: str, preco_max: int) -> List[dict]:
    """Busca produtos na Casas Bahia via API interna."""
    produtos = []

    params = {
        "q": keyword,
        "page": 1,
        "size": 20,
        "sortBy": "price",
        "sortOrder": "asc",
    }

    headers = {
        "User-Agent": random.choice(Config.USER_AGENTS),
        "Accept": "application/json",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Referer": "https://www.casasbahia.com.br/",
        "Origin": "https://www.casasbahia.com.br",
        "app-id": "casasbahia",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                CB_API_URL,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT),
                ssl=False,
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Casas Bahia retornou {resp.status} para '{keyword}'")
                    return []

                data = await resp.json(content_type=None)
                items = (
                    data.get("data", {})
                        .get("products", [])
                    or data.get("products", [])
                    or data.get("results", [])
                )

                for item in items[:15]:
                    produto = _processar_item_cb(item, keyword, preco_max)
                    if produto:
                        produtos.append(produto)

    except asyncio.TimeoutError:
        logger.warning(f"Timeout na Casas Bahia para '{keyword}'")
    except Exception as e:
        logger.error(f"Erro Casas Bahia scraper '{keyword}': {e}")

    return produtos


def _processar_item_cb(item: dict, keyword: str, preco_max: int) -> Optional[dict]:
    try:
        nome = (
            item.get("name")
            or item.get("title")
            or item.get("productName", "")
        )
        if not nome:
            return None

        # Preço atual — tenta vários campos possíveis da API
        preco = 0.0
        for campo in ["priceInfo", "price", "offers"]:
            bloco = item.get(campo, {})
            if isinstance(bloco, dict):
                preco = (
                    bloco.get("bestPrice")
                    or bloco.get("salePrice")
                    or bloco.get("price")
                    or bloco.get("minInstallmentValue", 0) * bloco.get("installmentCount", 1)
                    or 0
                )
                if preco:
                    break
        if not preco:
            preco = item.get("price") or item.get("salePrice") or 0

        preco = float(preco)
        if preco <= 0 or preco > preco_max:
            return None

        # Preço original
        preco_original = 0.0
        for campo in ["priceInfo", "price", "offers"]:
            bloco = item.get(campo, {})
            if isinstance(bloco, dict):
                preco_original = (
                    bloco.get("originalPrice")
                    or bloco.get("listPrice")
                    or bloco.get("regularPrice", 0)
                )
                if preco_original:
                    break
        if not preco_original:
            preco_original = item.get("listPrice") or item.get("originalPrice") or 0
        preco_original = float(preco_original)

        # Desconto
        desconto_pct = 0.0
        if preco_original > preco:
            desconto_pct = ((preco_original - preco) / preco_original) * 100

        # Link
        slug = item.get("slug") or item.get("url") or item.get("id", "")
        link = (
            slug if slug.startswith("http")
            else f"https://www.casasbahia.com.br/{slug}"
        )

        prod_id = hashlib.md5(f"cb_{item.get('id','')}_{preco}".encode()).hexdigest()

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
        logger.debug(f"Erro ao processar item Casas Bahia: {e}")
        return None
