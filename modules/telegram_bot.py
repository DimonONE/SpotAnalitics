import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.bot import DefaultBotProperties
from config import TELEGRAM_BOT_TOKEN, BOT_USER_ID, DEFAULT_BALANCE_USDT
from modules.database import get_all_open_forecasts, get_user_profile, get_all_forecasts

DB_FILE_PATH = "db.json"

# --- Инициализация бота и диспетчера ---
bot = Bot(
    token=TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="Markdown")
)
dp = Dispatcher()

# --- Форматирование сообщений ---
def format_signal_message(forecast):
    user_balance = DEFAULT_BALANCE_USDT
    entry = forecast['entry_price']
    sl = forecast['stop_loss_price']
    tp1 = forecast['take_profit1_price']
    tp2 = forecast['take_profit2_price']

    risk_percentage = ((entry - sl) / entry) * 100
    profit_percent = ((tp1 - entry) / entry) * 100
    profit_usd = user_balance * (profit_percent / 100)

    message = (
        f"⚡ **Сигнал** (ID: `{forecast['forecast_id'][:4]}`)\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Пара:** `{forecast['symbol']}`\n"
        f"⏱ **Таймфрейм:** `{forecast['timeframe']}`\n"
        f"📈 **Напрям:** *{forecast['direction']}*\n"
        f"💎 **Вхід:** `{entry:.6f}` USDT\n"
        f"🛡 **Стоп-лосс:** `{sl:.6f}` USDT\n"
        f"🎯 **ТП1:** `{tp1:.6f}` USDT\n"
        f"🎯 **ТП2:** `{tp2:.6f}` USDT\n"
        f"🔥 Потенційний прибуток: `{profit_usd:.4f}` USDT ({profit_percent:.2f}%)\n"
        f"⚠ Ризик: `{risk_percentage:.2f}%`\n"
        f"👤 Баланс користувача: `{user_balance}` USDT\n"
        f"🕒 Створено: `{forecast['created_at'].strftime('%Y-%m-%d %H:%M')} UTC`\n"
        f"🤖 _Сигнал відстежується автоматично._"
    )
    return message

def format_closure_message(closed_forecast):
    outcome_map = {
        'HIT_TP1': '✅ Take Profit 1 Hit',
        'HIT_TP2': '✅ Take Profit 2 Hit',
        'HIT_SL': '❌ Stop-Loss Hit'
    }
    duration_hours = closed_forecast.get('duration_seconds', 0) / 3600
    message = (
        f"🔔 **POSITION CLOSED** (ID: `{closed_forecast['forecast_id'][:4]}`)\n"
        f"**PAIR:** `{closed_forecast['symbol']}`\n"
        f"**OUTCOME:** {outcome_map.get(closed_forecast['outcome'], 'UNKNOWN')}\n"
        f"**Entry Price:** `{closed_forecast['entry_price']:.4f}`\n"
        f"**Hit Price:** `{closed_forecast['hit_price']:.4f}`\n"
        f"**Duration:** `{duration_hours:.2f}` hours"
    )
    return message

# --- Команды бота ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        """👋 **Welcome to SpotAnalitics Bot!**

I provide LONG trading signals.

**Commands:**
/status - open positions
/analytics - analytics
/get_db - get db.json file"""
    )

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    open_forecasts = get_all_open_forecasts()
    if not open_forecasts:
        await message.answer("No open positions.")
        return
    text = "**📊 Open Positions:**\n"
    for symbol, forecast in open_forecasts.items():
        text += f"{symbol} - Entry: {forecast['entry_price']}, SL: {forecast['stop_loss_price']}, TP1: {forecast['take_profit1_price']}\n\n\n"
    await message.answer(text)

@dp.message(Command("analytics"))
async def cmd_analytics(message: types.Message):
    forecasts = get_all_forecasts()
    if not forecasts:
        await message.answer("Нет данных для анализа.")
        return
    total = len(forecasts)
    wins = [f for f in forecasts if f.get('outcome') in ('HIT_TP1','HIT_TP2')]
    losses = [f for f in forecasts if f.get('outcome') == 'HIT_SL']
    await message.answer(
        f"Всего прогнозов: {total}\n"
        f"✅ Успешных: {len(wins)}\n"
        f"❌ Неудачных: {len(losses)}"
    )

@dp.message(Command("get_db"))
async def cmd_get_db(message: types.Message):
    if not os.path.exists(DB_FILE_PATH):
        await message.answer("❌ Файл db.json не найден.")
        return
    
    file = types.InputFile(DB_FILE_PATH)
    await message.answer_document(file, caption="📂 db.json")

# --- Функция для отправки сообщений вручную ---
async def send_message(user_id: int, message: str):
    await bot.send_message(chat_id=user_id, text=message, parse_mode="Markdown")
