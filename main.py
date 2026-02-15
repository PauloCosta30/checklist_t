"""
🚀 main.py — Entrypoint principal para o Render
   Inicia keep-alive server + bot Telegram
"""

from keep_alive import start_keep_alive
from bot import main

if __name__ == "__main__":
    start_keep_alive()
    main()
