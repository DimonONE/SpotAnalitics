import asyncio
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN
from modules.database import get_all_open_forecasts, get_user_profile

# This dictionary will store the user_id of the primary user.
# In a multi-user environment, this would be handled differently.
BOT_USER_ID = None

def format_signal_message(forecast):
    """Formats a forecast dictionary into a string for Telegram."""
    # Assuming a fixed user balance for now, will be dynamic later
    user_balance = 1200 # Dummy value
    risk_percentage = ((forecast['entry_price'] - forecast['stop_loss_price']) / forecast['entry_price']) * 100

    message = (
        f"🚀 **SIGNAL** (ID: `{forecast['forecast_id'][:4]}`)\n\n"
        f"**PAIR:** `{forecast['symbol']}`\n"
        f"**TIMEFRAME:** `{forecast['timeframe']}`\n"
        f"**DIRECTION:** `{forecast['direction']}`\n\n"
        f"**ENTRY:** `{forecast['entry_price']:.4f}` USDT\n"
        f"**STOP-LOSS:** `{forecast['stop_loss_price']:.4f}` USDT\n"
        f"**TAKE PROFIT 1:** `{forecast['take_profit1_price']:.4f}` USDT\n"
        f"**TAKE PROFIT 2:** `{forecast['take_profit2_price']:.4f}` USDT\n\n"
        f"**Risk:** `{risk_percentage:.2f}%` of entry (User balance: `{user_balance}` USDT)\n"
        f"**Created:** `{forecast['created_at'].strftime('%Y-%m-%d %H:%M')} UTC`\n\n"
        f"_Forecast will be tracked automatically._"
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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    global BOT_USER_ID
    BOT_USER_ID = update.message.from_user.id
    print(f"Bot started by user_id: {BOT_USER_ID}")
    
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
    
    return application

async def run_bot(application):
    """Runs the bot application."""
    print("Bot is polling for updates...")
    await application.run_polling()
