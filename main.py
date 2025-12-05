import schedule
import time
import asyncio
import threading
from config import EXCHANGE_ID, TOP_N_COINS_BY_VOLUME, DEFAULT_TIMEFRAME, BOT_USER_ID
from modules.data_fetcher import get_exchange, fetch_ohlcv, get_top_volume_symbols
from modules.indicator_calculator import add_indicators
from modules.signal_generator import check_long_signal
from modules.position_tracker import check_open_positions
from modules.database import get_open_forecast, add_open_forecast
from modules.telegram_bot import setup_bot, send_message, format_signal_message, format_closure_message

# --- Main Application Logic ---

async def run_analysis_cycle(exchange, bot):
    """
    The main job that runs on schedule. It checks for closed positions
    and scans for new signals.
    """
    print(f"\n[{time.ctime()}] Running analysis cycle...")
    
    # 1. Check the status of all open positions first
    closed_positions = check_open_positions(exchange)
    if closed_positions and BOT_USER_ID:
        print(f"Found {len(closed_positions)} closed position(s). Notifying user.")
        for closed in closed_positions:
            msg = format_closure_message(closed)
            # We need to run the async send_message in the bot's event loop
            await send_message(bot, BOT_USER_ID, msg)  


    # 2. Get the list of top coins to scan
    print(f"Fetching top {TOP_N_COINS_BY_VOLUME} coins by volume...")
    symbols_to_scan = get_top_volume_symbols(exchange, n=TOP_N_COINS_BY_VOLUME)
    
    if not symbols_to_scan:
        print("Could not fetch top symbols. Skipping scan for new signals.")
        return

    # 3. Scan for new signals
    print(f"Scanning for new signals across {len(symbols_to_scan)} symbols...")
    for symbol in symbols_to_scan:
        # Check if there's already an open signal for this symbol
        if get_open_forecast(symbol):
            print(f"-> Skipping {symbol}, position already open.")
            continue

        # Fetch data and calculate indicators
        ohlcv_data = fetch_ohlcv(exchange, symbol, DEFAULT_TIMEFRAME, limit=200)
        if ohlcv_data is None:
            print(f"-> Could not fetch data for {symbol}.")
            continue
            
        data = add_indicators(ohlcv_data)

        # Check for a signal
        forecast = check_long_signal(data, symbol, DEFAULT_TIMEFRAME)

        if forecast:
            print(f"✅ New signal found for {symbol}!")
            # Save the new forecast to the database
            add_open_forecast(forecast)
            
            # Send notification to the user
            if BOT_USER_ID:
                print("-> Sending signal to user...")
                msg = format_signal_message(forecast)
                await send_message(bot, BOT_USER_ID, msg)  # <-- заменили asyncio.run()

                
        else:
            # The signal_generator now prints the detailed reason.
            pass
    
    print("Analysis cycle finished.")


async def main():

    # Setup bot
    application = setup_bot()
    if not application:
        return
    bot = application.bot

    # Init exchange
    exchange = get_exchange(EXCHANGE_ID)
    if not exchange:
        print("Exchange init error")
        return

    print("Initialization complete.")

    # Schedule analysis
    schedule.every().hour.at(":01").do(
        lambda: asyncio.run_coroutine_threadsafe(
            run_analysis_cycle(exchange, bot),
            asyncio.get_event_loop()
        )
    )

    # Run first analysis
    # asyncio.create_task(run_analysis_cycle(exchange, bot))

    # --- Run telegram bot IN A SEPARATE THREAD ---
    def run_telegram():
        application.run_polling()

    tg_thread = threading.Thread(target=run_telegram, daemon=True)
    tg_thread.start()

    print("Bot polling started in background thread.")

    # # --- Scheduler loop ---
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
