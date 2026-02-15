"""
🛒 Scraper — Casas Bahia
   Usa a API pública do Grupo Magalu (mesma infra da CB)
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

# API pública do Grupo Casas Bahia (Via Varejo)
CB_SEARCH_API = "https://api.casasbahia.com.br/v1/search/products"


def _headers() -> dict:
    return {
        "User-Agent": random.choice(Config.USER_AGENTS),
        "Accept": "application/json",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Origin": "https://www.casasbahia.com.br",
        "Referer": "https://www.casasbahia.com.br/",
        "app-id": "casasbahia",
        "x-region": "SP",
        "x-locale": "pt_BR",
    }


def _parse_preco(valor) -> float:
    """Aceita float, int ou string 'R$ 1.299,99'"""
    try:
        if isinstance(valor, (int, float)):
            return float(valor)
        limpo = re.sub(r"[^\d,]", "", str(valor)).replace(",", ".")
        partes = limpo.split(".")
        if len(partes) > 2:
            limpo = "".join(partes[:-1]) + "." + partes[-1]
        return float(limpo) if limpo else 0.0
    except Exception:
        return 0.0


async def scrape_casasbahia(keyword: str, preco_max: int) -> List[dict]:
    """Busca produtos na Casas Bahia via API pública."""
    produtos = []

    # Tenta API JSON primeiro
    produtos = await _via_api(keyword, preco_max)

    # Se API falhar, tenta endpoint alternativo do BFF
    if not produtos:
        produtos = await _via_bff(keyword, preco_max)

    return produtos


async def _via_api(keyword: str, preco_max: int) -> List[dict]:
    """Tenta API principal da CB"""
    params = {
        "q": keyword,
        "page": 1,
        "size": 24,
        "sort": "price_asc",
    }

    try:
        await asyncio.sleep(random.uniform(1.0, 2.0))
        async with aiohttp.ClientSession() as session:
            async with session.get(
                CB_SEARCH_API,
                params=params,
                headers=_headers(),
                timeout=aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT),
                ssl=False,
            ) as resp:
                if resp.status != 200:
                    logger.debug(f"CB API retornou {resp.status} para '{keyword}'")
                    return []

                data = await resp.json(content_type=None)
                items = (
                    data.get("products")
                    or data.get("data", {}).get("products")
                    or data.get("results")
                    or []
                )

                produtos = []
                for item in items[:15]:
                    p = _extrair_produto(item, keyword, preco_max, "cb_api")
                    if p:
                        produtos.append(p)
                return produtos

    except Exception as e:
        logger.debug(f"CB API erro '{keyword}': {e}")
        return []


async def _via_bff(keyword: str, preco_max: int) -> List[dict]:
    """Tenta BFF alternativo compartilhado com Pontofrio/Extra"""
    bff_url = "https://api.casasbahia.com.br/bff/search/v1/search"
    params = {
        "query": keyword,
        "page": 1,
        "perPage": 20,
        "sort": "price:asc",
        "filter": f"price:[0 TO {preco_max}]",
    }
    headers = {**_headers(), "Accept": "application/json, text/plain, */*"}

    try:
        await asyncio.sleep(random.uniform(1.5, 2.5))
        async with aiohttp.ClientSession() as session:
            async with session.get(
                bff_url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT),
                ssl=False,
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Casas Bahia BFF retornou {resp.status} para '{keyword}'")
                    return []

                data = await resp.json(content_type=None)
                items = (
                    data.get("products")
                    or data.get("data", {}).get("products")
                    or data.get("hits")
                    or []
                )

                produtos = []
                for item in items[:15]:
                    p = _extrair_produto(item, keyword, preco_max, "cb_bff")
                    if p:
                        produtos.append(p)
                return produtos

    except Exception as e:
        logger.warning(f"Casas Bahia BFF erro '{keyword}': {e}")
        return []


def _extrair_produto(item: dict, keyword: str, preco_max: int, fonte: str) -> Optional[dict]:
    try:
        nome = (
            item.get("name")
            or item.get("title")
            or item.get("productName")
            or item.get("description", "")
        )
        if not nome:
            return None

        # Preço — tenta vários campos aninhados
        preco = 0.0
        for caminho in [
            ["priceInfo", "bestPrice"],
            ["priceInfo", "salePrice"],
            ["price", "bestPrice"],
            ["price", "salePrice"],
            ["offers", "primary", "price"],
            ["priceInfo", "price"],
        ]:
            bloco = item
            for k in caminho:
                bloco = bloco.get(k, {}) if isinstance(bloco, dict) else {}
            if isinstance(bloco, (int, float)) and bloco > 0:
                preco = float(bloco)
                break

        if not preco:
            preco = _parse_preco(item.get("price") or item.get("salePrice") or item.get("bestPrice", 0))

        if preco <= 0 or preco > preco_max:
            return None

        # Preço original
        preco_original = 0.0
        for caminho in [
            ["priceInfo", "originalPrice"],
            ["priceInfo", "listPrice"],
            ["price", "originalPrice"],
            ["price", "listPrice"],
        ]:
            bloco = item
            for k in caminho:
                bloco = bloco.get(k, {}) if isinstance(bloco, dict) else {}
            if isinstance(bloco, (int, float)) and bloco > 0:
                preco_original = float(bloco)
                break

        if not preco_original:
            preco_original = _parse_preco(
                item.get("originalPrice") or item.get("listPrice") or item.get("regularPrice", 0)
            )

        desconto_pct = 0.0
        if preco_original > preco:
            desconto_pct = ((preco_original - preco) / preco_original) * 100

        # Link
        slug = item.get("url") or item.get("slug") or item.get("id", "")
        link = slug if str(slug).startswith("http") else f"https://www.casasbahia.com.br/{slug}"

        prod_id = hashlib.md5(f"cb_{fonte}_{item.get('id', link)}_{preco}".encode()).hexdigest()

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
        logger.debug(f"Erro ao extrair produto CB: {e}")
        return None
