from datetime import datetime
from modules.database import get_all_open_forecasts, close_forecast
from modules.data_fetcher import get_exchange, fetch_ohlcv

def check_open_positions(exchange):
    """
    Iterates through all open forecasts, checks their status, and closes them if SL or TP is hit.

    :param exchange: The ccxt exchange instance.
    :return: A list of closed positions with their outcomes.
    """
    open_forecasts = get_all_open_forecasts()
    if not open_forecasts:
        return []

    closed_positions = []

    for symbol, forecast in open_forecasts.items():
        # Fetch the most recent candle to get the current price
        # We only need the last 2 candles to get the high/low of the last completed one.
        ohlcv = fetch_ohlcv(exchange, symbol, forecast['timeframe'], limit=2)
        
        if ohlcv is None or ohlcv.empty:
            print(f"Could not fetch price for {symbol} to check position.")
            continue
            
        # The latest price data is in the last row.
        # We check the high and low of the candle to see if a level was wicked to.
        last_candle = ohlcv.iloc[-1]
        current_high = last_candle['high']
        current_low = last_candle['low']

        sl_price = forecast['stop_loss_price']
        tp1_price = forecast['take_profit1_price']
        tp2_price = forecast['take_profit2_price']
        
        outcome = None
        hit_price = None
        
        # --- Check for SL or TP hit ---
        # Priority: SL -> TP2 -> TP1 because a single candle could hit multiple levels.
        
        # 1. Check for Stop-Loss
        if current_low <= sl_price:
            outcome = 'HIT_SL'
            hit_price = sl_price
            is_success = False
        
        # 2. Check for Take-Profit 2
        elif current_high >= tp2_price:
            outcome = 'HIT_TP2'
            hit_price = tp2_price
            is_success = True
            
        # 3. Check for Take-Profit 1
        elif current_high >= tp1_price:
            outcome = 'HIT_TP1'
            hit_price = tp1_price
            is_success = True

        if outcome:
            duration = (datetime.utcnow() - datetime.fromisoformat(forecast['created_at'])).total_seconds()
            
            outcome_data = {
                'hit_price': hit_price,
                'hit_at': datetime.utcnow(),
                'duration_seconds': duration,
                'outcome': outcome,
                'is_success': is_success
            }
            
            closed_forecast = close_forecast(symbol, outcome_data)
            
            if closed_forecast:
                print(f"✅ Position Closed: {symbol} | Outcome: {outcome} at {hit_price}")
                closed_positions.append(closed_forecast)

    return closed_positions


if __name__ == '__main__':
    # Example Usage (requires a dummy forecast in the db)
    from config import EXCHANGE_ID
    from modules.database import add_open_forecast, load_db, save_db
    import time
    import os

    # 1. Setup a dummy database state
    if os.path.exists('db.json'):
        os.remove('db.json')

    exchange_instance = get_exchange(EXCHANGE_ID)
    
    # Fetch real data to create a realistic test case
    real_data = fetch_ohlcv(exchange_instance, 'BTC/USDT', '1h', 1)
    if real_data is not None:
        current_price = real_data.iloc[-1]['close']
        
        # 2. Create a dummy forecast that will hit TP1 immediately
        dummy_tp_forecast = {
            'forecast_id': 'dummy-tp-test',
            'symbol': 'BTC/USDT',
            'direction': 'LONG',
            'timeframe': '1h',
            'created_at': datetime.utcnow().isoformat(),
            'entry_price': current_price * 0.99, # Cheaper entry
            'stop_loss_price': current_price * 0.98,
            'take_profit1_price': current_price, # TP1 is current price
            'take_profit2_price': current_price * 1.02,
        }
        add_open_forecast(dummy_tp_forecast)
        print(f"Added dummy forecast for BTC/USDT at entry: {dummy_tp_forecast['entry_price']:.2f}")

        # 3. Create another dummy forecast that should not close
        dummy_open_forecast = {
            'forecast_id': 'dummy-open-test',
            'symbol': 'ETH/USDT',
            'direction': 'LONG',
            'timeframe': '1h',
            'created_at': datetime.utcnow().isoformat(),
            'entry_price': 1000,
            'stop_loss_price': 900,
            'take_profit1_price': 1100,
            'take_profit2_price': 1200,
        }
        add_open_forecast(dummy_open_forecast)
        print(f"Added dummy forecast for ETH/USDT at entry: {dummy_open_forecast['entry_price']:.2f}")
        
        print("\n--- Running Position Tracker ---")
        time.sleep(1) # Ensure we don't hit rate limits
        
        # 4. Run the tracker
        closed_pos = check_open_positions(exchange_instance)
        
        # 5. Verify results
        db = load_db()
        assert len(closed_pos) == 1
        assert closed_pos[0]['outcome'] == 'HIT_TP1'
        assert 'ETH/USDT' in db['open_forecasts']
        assert 'BTC/USDT' not in db['open_forecasts']
        print("--- Position Tracker Test Passed ---")

        # Clean up
        if os.path.exists('db.json'):
            os.remove('db.json')
