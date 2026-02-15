"""
🔍 Monitor — Orquestrador central de todos os scrapers
   Coordena as buscas por categoria e retorna alertas formatados
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import List

from config import Config
from scrapers.mercadolivre import scrape_mercadolivre
from scrapers.amazon import scrape_amazon

logger = logging.getLogger("Monitor")

# ── ESTADO GLOBAL ──
_state = {
    "cycles": 0,
    "erros_total": 0,
    "ultimo_scan": "Nunca",
    "proximo_scan": "Aguardando...",
    "lojas": 2,
    "seen_ids": set(),  # evita alertar o mesmo produto duas vezes
}

# ── KEYWORDS POR CATEGORIA ──
CATEGORIAS = {
    "iphone": {
        "emoji": "📱",
        "nome": "iPhone",
        "keywords": [
            "iphone 15 pro max", "iphone 15 pro", "iphone 15",
            "iphone 14 pro max", "iphone 14", "iphone 13",
        ],
        "preco_max": Config.PRECO_MAX["iphone"],
    },
    "applewatch": {
        "emoji": "⌚",
        "nome": "Apple Watch",
        "keywords": [
            "apple watch series 9", "apple watch ultra 2",
            "apple watch se", "apple watch series 8",
        ],
        "preco_max": Config.PRECO_MAX["applewatch"],
    },
    "garmin": {
        "emoji": "🏃",
        "nome": "Garmin",
        "keywords": [
            "garmin forerunner 265", "garmin forerunner 255",
            "garmin fenix 7", "garmin epix", "garmin vivoactive 5",
        ],
        "preco_max": Config.PRECO_MAX["garmin"],
    },
    "perfume": {
        "emoji": "🌹",
        "nome": "Perfume",
        "keywords": [
            "dior sauvage 100ml", "chanel bleu 100ml",
            "hugo boss bottled", "paco rabanne 1 million",
            "armani acqua di gio", "burberry hero",
        ],
        "preco_max": Config.PRECO_MAX["perfume"],
    },
    "maquiagem": {
        "emoji": "💄",
        "nome": "Maquiagem",
        "keywords": [
            "base mac studio fix", "kit maquiagem mac",
            "urban decay all nighter", "lancôme teint idole",
            "charlotte tilbury flawless",
        ],
        "preco_max": Config.PRECO_MAX["maquiagem"],
    },
    "polo": {
        "emoji": "👕",
        "nome": "Polo Masculina",
        "keywords": [
            "camisa polo ralph lauren", "polo lacoste masculina",
            "polo reserva masculino", "polo tommy hilfiger",
        ],
        "preco_max": Config.PRECO_MAX["polo"],
    },
    "roupa": {
        "emoji": "🧥",
        "nome": "Roupa Masculina",
        "keywords": [
            "calça levis 511", "jaqueta nike masculina",
            "moletom adidas masculino", "calça jeans forum masculina",
            "jaqueta corta-vento masculina",
        ],
        "preco_max": Config.PRECO_MAX["roupa"],
    },
}


def get_status() -> dict:
    """Retorna estado atual do monitor"""
    now = datetime.now().strftime("%d/%m %H:%M")
    _state["proximo_scan"] = f"~{Config.SCAN_INTERVAL_MINUTES}min"
    return {**_state, "ultimo_scan": _state["ultimo_scan"]}


def formatar_alerta(produto: dict, categoria: dict) -> str:
    """Formata a mensagem de alerta para o Telegram (HTML)"""
    nome = produto.get("nome", "Produto")[:80]
    preco = produto.get("preco", 0)
    preco_original = produto.get("preco_original", 0)
    loja = produto.get("loja", "Loja")
    link = produto.get("link", "#")
    desconto = produto.get("desconto_pct", 0)

    # Formatação de preço BR
    preco_fmt = f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    preco_orig_fmt = f"R$ {preco_original:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    # Barra de urgência
    if desconto >= 70:
        urgencia = "🔴🔴🔴 ERRO ABSURDO"
    elif desconto >= 55:
        urgencia = "🔴🔴 ERRO GRAVE"
    else:
        urgencia = "🔴 ERRO DE PREÇO"

    msg = (
        f"{urgencia} {categoria['emoji']}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{nome}</b>\n\n"
        f"💰 <b>DE:</b> <s>{preco_orig_fmt}</s>\n"
        f"✅ <b>POR:</b> <b>{preco_fmt}</b> ({desconto:.0f}% OFF)\n\n"
        f"🏪 <b>Loja:</b> {loja}\n"
        f"📦 <b>Categoria:</b> {categoria['nome']}\n\n"
        f"🛒 <a href='{link}'><b>⚡ COMPRAR AGORA</b></a>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <i>Erro pode ser corrigido a qualquer momento!</i>\n"
        f"💥 <i>@ErroDePrecoBot</i>"
    )
    return msg


async def run_all_monitors() -> List[str]:
    """
    Executa todos os scrapers para todas as categorias.
    Retorna lista de mensagens formatadas para enviar no Telegram.
    """
    _state["cycles"] += 1
    _state["ultimo_scan"] = datetime.now().strftime("%d/%m %H:%M:%S")
    alertas = []

    for cat_key, cat_info in CATEGORIAS.items():
        for keyword in cat_info["keywords"]:
            logger.info(f"🔍 [{cat_info['nome']}] buscando: {keyword}")

            # Scraping em paralelo nas lojas disponíveis
            tasks = [
                scrape_mercadolivre(keyword, cat_info["preco_max"]),
                scrape_amazon(keyword, cat_info["preco_max"]),
            ]

            resultados = await asyncio.gather(*tasks, return_exceptions=True)

            for resultado in resultados:
                if isinstance(resultado, Exception):
                    logger.warning(f"Erro no scraper: {resultado}")
                    continue
                if not resultado:
                    continue

                for produto in resultado:
                    prod_id = produto.get("id", "")
                    desconto = produto.get("desconto_pct", 0)

                    # Filtrar: desconto mínimo + não alertado ainda
                    if desconto < Config.DESCONTO_MINIMO_PORCENTO:
                        continue
                    if prod_id in _state["seen_ids"]:
                        continue

                    _state["seen_ids"].add(prod_id)
                    _state["erros_total"] += 1
                    msg = formatar_alerta(produto, cat_info)
                    alertas.append(msg)
                    logger.info(
                        f"💥 ERRO ENCONTRADO: {produto.get('nome','?')[:40]} "
                        f"— {desconto:.0f}% OFF — R${produto.get('preco',0):.2f}"
                    )

            # Delay entre keywords para não ser bloqueado
            await asyncio.sleep(Config.REQUEST_DELAY + random.uniform(0.5, 1.5))

    # Limitar seen_ids para não crescer infinitamente (máx 2000)
    if len(_state["seen_ids"]) > 2000:
        _state["seen_ids"] = set(list(_state["seen_ids"])[-1000:])

    logger.info(f"✅ Ciclo {_state['cycles']} finalizado — {len(alertas)} alertas gerados")
    return alertas
