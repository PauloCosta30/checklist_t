"""
🛒 Scraper — Shopee Brasil
   Usa a API interna de busca da Shopee
"""

import asyncio
import hashlib
import logging
import random
import re
from typing import List, Optional

import aiohttp

from config import Config

logger = logging.getLogger("Shopee-Scraper")

SHOPEE_API = "https://shopee.com.br/api/v4/search/search_items"


def _headers() -> dict:
    return {
        "User-Agent": random.choice(Config.USER_AGENTS),
        "Accept": "application/json",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Referer": "https://shopee.com.br/",
        "Origin": "https://shopee.com.br",
        "x-api-source": "pc",
        "x-shopee-language": "pt-BR",
        "if-none-match-": "",
    }


def _parse_preco(centavos) -> float:
    """Shopee retorna preços em centavos × 100000"""
    try:
        return float(centavos) / 100000
    except Exception:
        return 0.0


async def scrape_shopee(keyword: str, preco_max: int) -> List[dict]:
    """Busca produtos na Shopee via API interna."""
    produtos = []

    params = {
        "by": "price",
        "keyword": keyword,
        "limit": 20,
        "newest": 0,
        "order": "asc",
        "page_type": "search",
        "scenario": "PAGE_GLOBAL_SEARCH",
        "version": 2,
        "price_min": 0,
        "price_max": preco_max * 100000,  # Shopee usa centavos × 100000
    }

    try:
        await asyncio.sleep(random.uniform(1.0, 2.5))
        async with aiohttp.ClientSession() as session:
            async with session.get(
                SHOPEE_API,
                params=params,
                headers=_headers(),
                timeout=aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT),
                ssl=False,
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Shopee retornou {resp.status} para '{keyword}'")
                    return []

                data = await resp.json(content_type=None)
                items = data.get("items", [])

                for item in items[:20]:
                    produto = _processar_item(item, keyword, preco_max)
                    if produto:
                        produtos.append(produto)

    except asyncio.TimeoutError:
        logger.warning(f"Timeout Shopee '{keyword}'")
    except Exception as e:
        logger.error(f"Erro Shopee scraper '{keyword}': {e}")

    return produtos


def _processar_item(item: dict, keyword: str, preco_max: int) -> Optional[dict]:
    try:
        info = item.get("item_basic", item)

        nome = info.get("name", "")
        if not nome:
            return None

        # Preço atual
        preco_raw = (
            info.get("price_min")
            or info.get("price")
            or info.get("price_min_before_discount")
            or 0
        )
        preco = _parse_preco(preco_raw)
        if preco <= 0 or preco > preco_max:
            return None

        # Preço original (antes do desconto)
        preco_orig_raw = (
            info.get("price_before_discount")
            or info.get("price_min_before_discount")
            or 0
        )
        preco_original = _parse_preco(preco_orig_raw)

        # Desconto
        desconto_pct = 0.0
        raw_discount = info.get("raw_discount") or info.get("discount") or 0
        if raw_discount and float(raw_discount) > 0:
            desconto_pct = float(raw_discount)
        elif preco_original > preco and preco_original > 0:
            desconto_pct = ((preco_original - preco) / preco_original) * 100

        # Link
        shop_id = info.get("shopid", "")
        item_id = info.get("itemid", "") or info.get("id", "")
        nome_slug = re.sub(r"[^a-z0-9]+", "-", nome.lower())[:50]
        link = f"https://shopee.com.br/{nome_slug}-i.{shop_id}.{item_id}"

        prod_id = hashlib.md5(f"sh_{shop_id}_{item_id}_{preco}".encode()).hexdigest()

        return {
            "id": prod_id,
            "nome": nome,
            "preco": preco,
            "preco_original": preco_original if preco_original > preco else 0,
            "desconto_pct": desconto_pct,
            "loja": "Shopee",
            "link": link,
            "keyword": keyword,
        }

    except Exception as e:
        logger.debug(f"Erro ao processar item Shopee: {e}")
        return None
