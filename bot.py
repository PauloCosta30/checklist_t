"""
╔══════════════════════════════════════════════╗
║       💥 ERRO DE PREÇO BOT — Main            ║
║   Bot Telegram de monitoramento de erros     ║
╚══════════════════════════════════════════════╝
"""

import asyncio
import logging
from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from monitor import run_all_monitors, get_status
from config import Config

# ── LOGGING ──
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%d/%m %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("ErroBot")


# ── COMANDOS ──
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "💥 <b>ERRO DE PREÇO BOT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 Olá! Estou monitorando erros de preço 24h em:\n\n"
        "📱 <b>iPhone</b> — todas as gerações\n"
        "⌚ <b>Apple Watch</b> — Series &amp; Ultra\n"
        "🏃 <b>Garmin</b> — GPS esportivos\n"
        "🌹 <b>Perfumes</b> — importados originais\n"
        "💄 <b>Maquiagem</b> — marcas premium\n"
        "👕 <b>Polo Masculina</b> — marcas top\n"
        "🧥 <b>Roupa Masculina</b> — completo\n\n"
        "📡 Alertas chegam aqui automaticamente!\n\n"
        "📋 <b>Comandos:</b>\n"
        "/status — ver status do monitor\n"
        "/categorias — categorias ativas\n"
        "/ping — testar bot"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = get_status()
    msg = (
        "📊 <b>STATUS DO MONITOR</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔄 Ciclos executados: <code>{status['cycles']}</code>\n"
        f"🎯 Erros encontrados: <code>{status['erros_total']}</code>\n"
        f"⏱ Último scan: <code>{status['ultimo_scan']}</code>\n"
        f"⏰ Próximo scan: <code>{status['proximo_scan']}</code>\n"
        f"🏪 Lojas monitoradas: <code>Mercado Livre, Amazon, Casas Bahia, Magalu</code>\n\n"
        "✅ Bot operacional!"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_categorias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🗂 <b>CATEGORIAS MONITORADAS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 iPhone 13, 14, 15, Pro, Pro Max\n"
        "⌚ Apple Watch S9, Ultra 2, SE\n"
        "🏃 Garmin Forerunner, Fenix, Vivoactive, Epix\n"
        "🌹 Dior Sauvage, Chanel, Hugo Boss, Paco Rabanne\n"
        "💄 MAC, Urban Decay, Lancôme, Charlotte Tilbury\n"
        "👕 Polo Ralph Lauren, Lacoste, Reserva, Tommy\n"
        "🧥 Calças, Jaquetas, Moletons — Levi's, Nike, Adidas\n\n"
        "🔍 Lojas: Mercado Livre, Amazon BR, Casas Bahia, Magazine Luiza"
    )
    await update.message.reply_text(msg, parse_mode="HTML")


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! Bot online e funcionando!")


async def msg_desconhecido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Comando não reconhecido. Use /start para ver os comandos disponíveis."
    )


# ── SCHEDULER JOB ──
async def job_monitor(context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔍 Iniciando ciclo de monitoramento...")
    try:
        erros = await run_all_monitors()
        if erros:
            bot: Bot = context.bot
            for erro in erros:
                try:
                    await bot.send_message(
                        chat_id=Config.TELEGRAM_CHAT_ID,
                        text=erro,
                        parse_mode="HTML",
                        disable_web_page_preview=False,
                    )
                    await asyncio.sleep(1.5)
                except Exception as e:
                    logger.error(f"Erro ao enviar mensagem: {e}")
            logger.info(f"✅ {len(erros)} alertas enviados")
        else:
            logger.info("ℹ️ Nenhum erro de preço encontrado neste ciclo")
    except Exception as e:
        logger.error(f"❌ Erro no ciclo de monitoramento: {e}")


# ── MAIN ──
def main():
    logger.info("🚀 Iniciando Erro de Preço Bot...")

    if not Config.TELEGRAM_TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN não configurado!")
    if not Config.TELEGRAM_CHAT_ID:
        raise ValueError("❌ TELEGRAM_CHAT_ID não configurado!")

    app = Application.builder().token(Config.TELEGRAM_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("categorias", cmd_categorias))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_desconhecido))

    # Scheduler
    interval = Config.SCAN_INTERVAL_MINUTES * 60
    app.job_queue.run_repeating(
        job_monitor,
        interval=interval,
        first=30,
        name="monitor_job",
    )

    logger.info(f"✅ Bot iniciado! Monitorando a cada {Config.SCAN_INTERVAL_MINUTES} minutos.")
    logger.info(f"📡 Canal: {Config.TELEGRAM_CHAT_ID}")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
