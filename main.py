import asyncio
import schedule
import time
from config import EXCHANGE_ID, TOP_N_COINS_BY_VOLUME, DEFAULT_TIMEFRAME, BOT_USER_ID
from modules.data_fetcher import get_exchange, fetch_ohlcv, get_top_volume_symbols
from modules.indicator_calculator import add_indicators
from modules.signal_generator import check_long_signal
from modules.position_tracker import check_open_positions
from modules.database import get_open_forecast, add_open_forecast
from modules.telegram_bot import dp, bot, send_message, format_signal_message, format_closure_message

# --- Основной цикл анализа ---
async def run_analysis_cycle(exchange):
    print(f"\n[{time.ctime()}] Running analysis cycle...")

    closed_positions = await asyncio.to_thread(check_open_positions, exchange)
    if closed_positions and BOT_USER_ID:
        for closed in closed_positions:
            msg = format_closure_message(closed)
            await send_message(BOT_USER_ID, msg)

    symbols = await asyncio.to_thread(get_top_volume_symbols, exchange, TOP_N_COINS_BY_VOLUME)
    if not symbols:
        return

    for symbol in symbols:
        if await asyncio.to_thread(get_open_forecast, symbol):
            continue

        ohlcv_data = await asyncio.to_thread(fetch_ohlcv, exchange, symbol, DEFAULT_TIMEFRAME, 200)
        if ohlcv_data is None:
            continue

        data = await asyncio.to_thread(add_indicators, ohlcv_data)

        # Генерация сигнала
        forecast = await asyncio.to_thread(check_long_signal, data, symbol, DEFAULT_TIMEFRAME)
        if forecast:
            print(f"✅ New signal found for {symbol}!")
            await asyncio.to_thread(add_open_forecast, forecast)
            if BOT_USER_ID:
                msg = format_signal_message(forecast)
                await send_message(BOT_USER_ID, msg)

    print("Analysis cycle finished.")

# --- Периодический запуск через schedule ---
async def scheduler_loop(exchange):
    schedule.every().hour.at(":01").do(lambda: asyncio.create_task(run_analysis_cycle(exchange)))
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

# --- Главная функция ---
async def main():
    print("Initializing exchange...")
    exchange = get_exchange("binance")

    if not exchange:
        print("Exchange init error")
        return

    # --- ВАЖНО: первый анализ в фоне, не блокирует polling ---
    print("Scheduling first analysis...")
    asyncio.create_task(run_analysis_cycle(exchange))

    # --- Настройка ежечасного запуска ---
    schedule.every().hour.at(":01").do(
        lambda: asyncio.create_task(run_analysis_cycle(exchange))
    )

    # Запускаем внутренний цикл планировщика
    asyncio.create_task(scheduler_loop(exchange))

    print("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
