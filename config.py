"""
⚙️  Config — Todas as variáveis de ambiente do bot
    Configure no painel do Render em Environment Variables
"""

import os


class Config:
    # ── TELEGRAM ──
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # ── MONITOR ──
    # Intervalo entre scans (minutos) — recomendado 15 no Render free
    SCAN_INTERVAL_MINUTES: int = int(os.getenv("SCAN_INTERVAL_MINUTES", "5"))

    # Desconto mínimo para considerar "erro de preço" (%)
    DESCONTO_MINIMO_PORCENTO: int = int(os.getenv("DESCONTO_MINIMO_PORCENTO", "40"))

    # Preços máximos por categoria (R$) — acima disso ignora
    # Ajuste conforme sua realidade de mercado
    PRECO_MAX = {
        "iphone": int(os.getenv("PRECO_MAX_IPHONE", "6000")),
        "applewatch": int(os.getenv("PRECO_MAX_APPLEWATCH", "3000")),
        "garmin": int(os.getenv("PRECO_MAX_GARMIN", "2500")),
        "perfume": int(os.getenv("PRECO_MAX_PERFUME", "800")),
        "maquiagem": int(os.getenv("PRECO_MAX_MAQUIAGEM", "500")),
        "polo": int(os.getenv("PRECO_MAX_POLO", "300")),
        "roupa": int(os.getenv("PRECO_MAX_ROUPA", "500")),
    }

    # ── SCRAPING ──
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "12"))
    REQUEST_DELAY: float = float(os.getenv("REQUEST_DELAY", "2.0"))

    # User-Agent rotativo
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    # ── RENDER / KEEP-ALIVE ──
    PORT: int = int(os.getenv("PORT", "10000"))
