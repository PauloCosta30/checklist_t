"""
╔══════════════════════════════════════════════╗
║       💥 ERRO DE PREÇO BOT — Main            ║
║   Bot Telegram de monitoramento de erros     ║
╚══════════════════════════════════════════════╝
"""

import asyncio
import logging
import os
from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from monitor import run_all_monitors
from config import Config

# ── LOGGING ──
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%d/%m %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("ErroBot")


# ── COMANDOS ──
async def cmd_start(update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start — boas-vindas"""
    msg = (
        "💥 *ERRO DE PREÇO BOT*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 Olá\\! Estou monitorando erros de preço 24h por dia em:\n\n"
        "📱 *iPhone* — todas as gerações\n"
        "⌚ *Apple Watch* — Series & Ultra\n"
        "🏃 *Garmin* — GPS esportivos\n"
        "🌹 *Perfumes* — importados originais\n"
        "💄 *Maquiagem* — marcas premium\n"
        "👕 *Polo Masculina* — marcas top\n"
        "🧥 *Roupa Masculina* — completo\n\n"
        "📡 Alertas chegam aqui automaticamente\\!\n\n"
        "📋 *Comandos:*\n"
        "/status — ver status do monitor\n"
        "/categorias — categorias ativas\n"
        "/ping — testar bot\n"
    )
    await update.message.reply_text(msg, parse_mode="MarkdownV2")


async def cmd_status(update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status — status do monitoramento"""
    from monitor import get_status
    status = get_status()
    msg = (
        "📊 *STATUS DO MONITOR*\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔄 Ciclos executados: `{status['cycles']}`\n"
        f"🎯 Erros encontrados: `{status['erros_total']}`\n"
        f"⏱ Último scan: `{status['ultimo_scan']}`\n"
        f"⏰ Próximo scan: `{status['proximo_scan']}`\n"
        f"🏪 Lojas monitoradas: `{status['lojas']}`\n\n"
        "✅ Bot operacional\\!"
    )
    await update.message.reply_text(msg, parse_mode="MarkdownV2")


async def cmd_categorias(update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /categorias — lista categorias ativas"""
    msg = (
        "🗂 *CATEGORIAS MONITORADAS*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📱 iPhone 13, 14, 15, Pro, Pro Max\n"
        "⌚ Apple Watch S9, Ultra 2, SE\n"
        "🏃 Garmin Forerunner, Fenix, Vivoactive, Epix\n"
        "🌹 Dior Sauvage, Chanel, Hugo Boss, Paco Rabanne\n"
        "💄 MAC, Urban Decay, Lancôme, Charlotte Tilbury\n"
        "👕 Polo Ralph Lauren, Lacoste, Reserva, Tommy\n"
        "🧥 Calças, Jaquetas, Moletons \\— Levi's, Nike, Adidas\n\n"
        "🔍 Lojas: Mercado Livre, Amazon BR, Magazine Luiza,\n"
        "Americanas, Shopee, Casas Bahia, Kabum\\!\n"
    )
    await update.message.reply_text(msg, parse_mode="MarkdownV2")


async def cmd_ping(update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ping — teste de resposta"""
    await update.message.reply_text("🏓 Pong\\! Bot online e funcionando\\!", parse_mode="MarkdownV2")


async def msg_desconhecido(update, context: ContextTypes.DEFAULT_TYPE):
    """Mensagem não reconhecida"""
    await update.message.reply_text(
        "❓ Comando não reconhecido\\. Use /start para ver os comandos disponíveis\\.",
        parse_mode="MarkdownV2"
    )


# ── SCHEDULER JOB ──
async def job_monitor(context: ContextTypes.DEFAULT_TYPE):
    """Job agendado — roda o monitor e envia alertas"""
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
                    await asyncio.sleep(1)  # evitar flood
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

    # Registrar comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("categorias", cmd_categorias))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_desconhecido))

    # Scheduler — roda o monitor a cada X minutos
    job_queue = app.job_queue
    interval = Config.SCAN_INTERVAL_MINUTES * 60
    job_queue.run_repeating(
        job_monitor,
        interval=interval,
        first=30,  # primeiro scan 30s após iniciar
        name="monitor_job",
    )

    logger.info(f"✅ Bot iniciado! Monitorando a cada {Config.SCAN_INTERVAL_MINUTES} minutos.")
    logger.info(f"📡 Canal: {Config.TELEGRAM_CHAT_ID}")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
