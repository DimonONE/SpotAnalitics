import asyncio
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN, BOT_USER_ID, DEFAULT_BALANCE_USDT
from modules.database import get_all_open_forecasts, get_user_profile, get_all_forecasts
import os

DB_FILE_PATH = "db.json"  # путь к файлу базы данных

def format_signal_message(forecast):
    """Форматує прогноз у повідомлення для Telegram українською мовою."""
    
    user_balance = DEFAULT_BALANCE_USDT  # Тимчасове значення

    entry = forecast['entry_price']
    sl = forecast['stop_loss_price']
    tp1 = forecast['take_profit1_price']
    tp2 = forecast['take_profit2_price']

    risk_percentage = ((entry - sl) / entry) * 100
    profit_percent = ((tp1 - entry) / entry) * 100
    profit_usd = user_balance * (profit_percent / 100)

    message = (
        f"⚡ ** Сигнал ** (ID: `{forecast['forecast_id'][:4]}`)\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"

        f"📌 **Пара:** `{forecast['symbol']}`\n"
        f"⏱ **Таймфрейм:** `{forecast['timeframe']}`\n"
        f"📈 **Напрям:** *{forecast['direction']}*\n\n"

        f"💎 **Вхід:** `{entry:.6f}` USDT\n"
        f"🛡 **Стоп-лосс:** `{sl:.6f}` USDT\n"
        f"🎯 **ТП1:** `{tp1:.6f}` USDT \n"
        f"🎯 **ТП2:** `{tp2:.6f}` USDT \n\n"

        f"🔥 **Потенційний прибуток:**\n"
        f"   • 💵 `{profit_usd:.4f}` USDT\n"
        f"   • 📊 `{profit_percent:.2f}%`\n\n"

        f"⚠ **Ризик:** `{risk_percentage:.2f}%` від входу\n"
        f"👤 Баланс користувача: `{user_balance}` USDT\n"
        f"🕒 Створено: `{forecast['created_at'].strftime('%Y-%m-%d %H:%M')} UTC`\n\n"

        f"🤖 _Сигнал відстежується автоматично._"
    )
 
    return message

def format_closure_message(closed_forecast):
    """Formats a closed forecast message."""
    outcome_map = {
        'HIT_TP1': '✅ Take Profit 1 Hit',
        'HIT_TP2': '✅ Take Profit 2 Hit',
        'HIT_SL': '❌ Stop-Loss Hit'
    }
    
    duration_hours = closed_forecast.get('duration_seconds', 0) / 3600

    message = (
        f"🔔 **POSITION CLOSED** (ID: `{closed_forecast['forecast_id'][:4]}`)\n\n"
        f"**PAIR:** `{closed_forecast['symbol']}`\n"
        f"**OUTCOME:** {outcome_map.get(closed_forecast['outcome'], 'UNKNOWN')}\n\n"
        f"**Entry Price:** `{closed_forecast['entry_price']:.4f}`\n"
        f"**Hit Price:** `{closed_forecast['hit_price']:.4f}`\n"
        f"**Duration:** `{duration_hours:.2f}` hours\n"
    )
    return message


async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет аналитику по прогнозам из базы данных."""
    forecasts = get_all_forecasts()
    
    if not forecasts:
        await update.message.reply_text("📊 Нет данных для анализа.")
        return

    total = len(forecasts)
    wins = [f for f in forecasts if f.get('outcome') in ('HIT_TP1', 'HIT_TP2')]
    losses = [f for f in forecasts if f.get('outcome') == 'HIT_SL']

    win_percent = (len(wins) / total) * 100
    loss_percent = (len(losses) / total) * 100

    total_profit_usd = sum(
        (f['take_profit1_price'] - f['entry_price']) if f.get('outcome') == 'HIT_TP1' else
        (f['take_profit2_price'] - f['entry_price']) if f.get('outcome') == 'HIT_TP2' else
        (f['stop_loss_price'] - f['entry_price']) for f in forecasts
    )

    message = (
        f"📊 **Аналітика прогнозів**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Всього прогнозів: {total}\n"
        f"✅ Успішних (TP1/TP2): {len(wins)} ({win_percent:.2f}%)\n"
        f"❌ Невдалих (SL): {len(losses)} ({loss_percent:.2f}%)\n"
        f"💵 Сумарний прибуток/збиток: {total_profit_usd:.2f} USDT\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"**Деталі прогнозів:**\n"
    )

    for f in forecasts[-10:]:  # выводим последние 10 прогнозов
        outcome_emoji = "✅" if f.get('outcome') in ('HIT_TP1', 'HIT_TP2') else "❌"
        profit = (
            f['take_profit1_price'] - f['entry_price']
            if f.get('outcome') == 'HIT_TP1' else
            f['take_profit2_price'] - f['entry_price']
            if f.get('outcome') == 'HIT_TP2' else
            f['stop_loss_price'] - f['entry_price']
        )
        message += (
            f"{outcome_emoji} `{f['symbol']}`: {profit:.4f} USDT "
            f"(Entry: {f['entry_price']:.4f}, TP1: {f['take_profit1_price']:.4f}, "
            f"TP2: {f['take_profit2_price']:.4f}, SL: {f['stop_loss_price']:.4f})\n"
        )

    await update.message.reply_text(message, parse_mode='Markdown')

async def get_db_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет файл db.json пользователю."""
    if not os.path.exists(DB_FILE_PATH):
        await update.message.reply_text("❌ Файл db.json не найден.")
        return

    # Отправляем файл
    try:
        await update.message.reply_document(document=open(DB_FILE_PATH, 'rb'),
                                            filename="db.json",
                                            caption="📂 Ваш файл базы данных db.json")
    except Exception as e:
        await update.message.reply_text(f"❌ Не удалось отправить файл: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    
    await update.message.reply_text(
        "👋 **Welcome to SpotAnalitics Bot!**\n\n"
        "I will provide LONG trading signals based on the pre-defined strategy.\n\n"
        "**Available Commands:**\n"
        "- `/start` - Initialize the bot\n"
        "- `/status` - View open positions and stats\n\n"
        "I will start scanning for signals shortly."
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /status command."""
    open_forecasts = get_all_open_forecasts()
    if not open_forecasts:
        await update.message.reply_text("No open positions being tracked.")
        return

    message = "**📊 Open Positions:**\n\n"
    for symbol, forecast in open_forecasts.items():
        message += (
            f"**{symbol}** (ID: `{forecast['forecast_id'][:4]}`)\n"
            f"  - Entry: `{forecast['entry_price']:.4f}`\n"
            f"  - SL: `{forecast['stop_loss_price']:.4f}`\n"
            f"  - TP1: `{forecast['take_profit1_price']:.4f}`\n\n"
        )
    await update.message.reply_text(message)

async def send_message(bot: Bot, user_id: int, message: str):
    """Sends a message to a specific user."""
    await bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')

def setup_bot():
    """Sets up the bot, its command handlers, and returns the application object."""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print("Error: Telegram bot token is not configured. Please edit config.py")
        return None

    print("Setting up Telegram bot...")
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("get_db", get_db_command))
    application.add_handler(CommandHandler("analytics", analytics_command))
    
    return application

