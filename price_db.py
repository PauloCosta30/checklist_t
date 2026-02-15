"""
💾 Price DB — Banco de preços históricos (arquivo JSON local)
   Salva o histórico de preços por produto para detectar quedas bruscas
"""

import json
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("PriceDB")

DB_FILE = "price_history.json"


def _load() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(db: dict):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Erro ao salvar price_db: {e}")


def get_historico(prod_id: str) -> list:
    """Retorna histórico de preços de um produto"""
    db = _load()
    return db.get(prod_id, {}).get("historico", [])


def get_preco_referencia(prod_id: str) -> Optional[float]:
    """Retorna o preço de referência (mediana histórica) do produto"""
    db = _load()
    historico = db.get(prod_id, {}).get("historico", [])
    if not historico:
        return None
    precos = [h["preco"] for h in historico]
    precos_sorted = sorted(precos)
    n = len(precos_sorted)
    # mediana
    if n % 2 == 0:
        return (precos_sorted[n // 2 - 1] + precos_sorted[n // 2]) / 2
    return precos_sorted[n // 2]


def registrar_preco(prod_id: str, nome: str, preco: float, loja: str):
    """Registra o preço atual no histórico"""
    db = _load()
    if prod_id not in db:
        db[prod_id] = {"nome": nome, "historico": []}

    historico = db[prod_id]["historico"]
    historico.append({
        "preco": preco,
        "loja": loja,
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
    })

    # Manter apenas os últimos 60 registros por produto
    db[prod_id]["historico"] = historico[-60:]
    _save(db)


def preco_minimo_historico(prod_id: str) -> Optional[float]:
    """Retorna o menor preço já visto para este produto"""
    historico = get_historico(prod_id)
    if not historico:
        return None
    return min(h["preco"] for h in historico)
