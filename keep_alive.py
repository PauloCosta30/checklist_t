"""
🌐 Keep-Alive Server — Mantém o bot acordado no Render (free tier)
   O Render free hiberna serviços sem requisições HTTP.
   Este servidor responde pings e mantém tudo vivo.
"""

import threading
import logging
from flask import Flask, jsonify
from datetime import datetime
from config import Config

logger = logging.getLogger("KeepAlive")
app = Flask(__name__)

_start_time = datetime.now()


@app.route("/")
def home():
    uptime = str(datetime.now() - _start_time).split(".")[0]
    return jsonify({
        "status": "🟢 online",
        "bot": "Erro de Preço Bot",
        "uptime": uptime,
        "message": "💥 Bot monitorando erros de preço 24/7",
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.route("/ping")
def ping():
    return "pong", 200


def run_server():
    """Roda o servidor Flask via Werkzeug (sem warning de produção)"""
    from werkzeug.serving import make_server
    server = make_server("0.0.0.0", Config.PORT, app)
    server.serve_forever()


def start_keep_alive():
    """Inicia o servidor de keep-alive em background"""
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    logger.info(f"🌐 Keep-alive server iniciado na porta {Config.PORT}")
