"""
🔎 Detector — Motor de detecção de erro de preço
   Usa 3 camadas combinadas para detectar erros mesmo sem preço riscado

   CAMADA 1 → Preço riscado da loja (desconto explícito)
   CAMADA 2 → Preço mínimo fixo por categoria (limiar absoluto)
   CAMADA 3 → Queda brusca vs histórico (mediana dos últimos preços)
"""

import logging
from typing import Optional, Tuple
from config import Config
from price_db import get_preco_referencia, preco_minimo_historico, registrar_preco

logger = logging.getLogger("Detector")

# ── PREÇOS MÍNIMOS ABSOLUTOS POR CATEGORIA ──
# Abaixo destes valores = quase certamente erro de preço
PRECO_MINIMO_ABSOLUTO = {
    "iphone":      1800.0,   # iPhone abaixo de R$1.800 = erro
    "applewatch":   700.0,   # Apple Watch abaixo de R$700 = erro
    "garmin":       600.0,   # Garmin abaixo de R$600 = erro
    "perfume":       80.0,   # Perfume importado abaixo de R$80 = erro
    "maquiagem":     50.0,   # Maquiagem premium abaixo de R$50 = erro
    "polo":          40.0,   # Polo original abaixo de R$40 = erro
    "roupa":         35.0,   # Roupa masculina abaixo de R$35 = erro
}

# Queda % mínima no histórico para considerar erro
QUEDA_HISTORICO_MINIMA = 40  # 40% abaixo da mediana histórica


def analisar_produto(
    produto: dict,
    categoria_key: str,
) -> Tuple[bool, str, float]:
    """
    Analisa se um produto é erro de preço usando as 3 camadas.

    Retorna: (é_erro, motivo, desconto_pct)
    """
    prod_id  = produto.get("id", "")
    nome     = produto.get("nome", "")
    preco    = produto.get("preco", 0.0)
    loja     = produto.get("loja", "")
    preco_original = produto.get("preco_original", 0.0)

    if preco <= 0:
        return False, "", 0.0

    # ── Registra preço no histórico (sempre) ──
    registrar_preco(prod_id, nome, preco, loja)

    # ────────────────────────────────────────
    # CAMADA 1 — Desconto explícito da loja
    # ────────────────────────────────────────
    if preco_original > preco:
        desconto = ((preco_original - preco) / preco_original) * 100
        if desconto >= Config.DESCONTO_MINIMO_PORCENTO:
            return True, f"🏷️ Desconto da loja: {desconto:.0f}% OFF", desconto

    # ────────────────────────────────────────
    # CAMADA 2 — Preço abaixo do mínimo absoluto
    # ────────────────────────────────────────
    limite = PRECO_MINIMO_ABSOLUTO.get(categoria_key, 0)
    if limite > 0 and preco < limite:
        desconto_estimado = ((limite - preco) / limite) * 100
        return (
            True,
            f"🚨 Preço abaixo do mínimo de mercado (ref: R${limite:,.0f})",
            desconto_estimado,
        )

    # ────────────────────────────────────────
    # CAMADA 3 — Queda brusca vs histórico
    # ────────────────────────────────────────
    referencia = get_preco_referencia(prod_id)
    if referencia and referencia > 0:
        queda = ((referencia - preco) / referencia) * 100
        if queda >= QUEDA_HISTORICO_MINIMA:
            return (
                True,
                f"📉 Queda de {queda:.0f}% vs histórico (antes: R${referencia:,.2f})",
                queda,
            )

    return False, "", 0.0
