"""
🛒 Scraper — Mercado Livre
   Busca produtos com erro de preço via API pública do ML
"""

import asyncio
import hashlib
import logging
import random
import aiohttp
from typing import List, Optional

from config import Config

logger = logging.getLogger("ML-Scraper")

ML_API_URL = "https://api.mercadolibre.com/sites/MLB/search"


async def scrape_mercadolivre(keyword: str, preco_max: int) -> List[dict]:
    """
    Busca produtos no Mercado Livre via API oficial.
    Retorna lista de produtos que parecem erro de preço.
    """
    produtos = []

    params = {
        "q": keyword,
        "condition": "new",
        "sort": "price_asc",
        "limit": 20,
        "price": f"0-{preco_max}",
    }

    headers = {
        "User-Agent": random.choice(Config.USER_AGENTS),
        "Accept": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                ML_API_URL,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"ML retornou {resp.status} para '{keyword}'")
                    return []

                data = await resp.json()
                items = data.get("results", [])

                for item in items:
                    produto = _processar_item_ml(item, keyword)
                    if produto:
                        produtos.append(produto)

    except asyncio.TimeoutError:
        logger.warning(f"Timeout no ML para '{keyword}'")
    except Exception as e:
        logger.error(f"Erro ML scraper '{keyword}': {e}")

    return produtos


def _processar_item_ml(item: dict, keyword: str) -> Optional[dict]:
    """Processa um item do ML e verifica se é erro de preço"""
    try:
        preco = float(item.get("price", 0))
        if preco <= 0:
            return None

        # Preço original (antes do desconto)
        preco_original = preco
        atributos = item.get("attributes", [])
        for attr in atributos:
            if attr.get("id") == "ORIGINAL_PRICE":
                try:
                    preco_original = float(attr["value_struct"]["number"])
                except Exception:
                    pass

        # Tentar pegar original_price do campo direto
        if item.get("original_price") and item["original_price"] > preco:
            preco_original = float(item["original_price"])

        # Calcular desconto
        if preco_original <= preco or preco_original <= 0:
            # Sem desconto explícito — estimar pelo preço de mercado típico
            # (vai filtrar pelo monitor com DESCONTO_MINIMO_PORCENTO)
            return None

        desconto_pct = ((preco_original - preco) / preco_original) * 100

        # ID único para deduplicação
        prod_id = hashlib.md5(f"ml_{item.get('id','')}_{preco}".encode()).hexdigest()

        return {
            "id": prod_id,
            "nome": item.get("title", "Produto sem nome"),
            "preco": preco,
            "preco_original": preco_original,
            "desconto_pct": desconto_pct,
            "loja": "Mercado Livre",
            "link": item.get("permalink", "#"),
            "keyword": keyword,
            "seller": item.get("seller", {}).get("nickname", ""),
            "disponivel": item.get("available_quantity", 0),
        }

    except Exception as e:
        logger.debug(f"Erro ao processar item ML: {e}")
        return None
