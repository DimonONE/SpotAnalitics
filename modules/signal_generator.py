from datetime import datetime
import uuid
from config import (
    DEFAULT_SL_METHOD, 
    DEFAULT_ATR_MULTIPLIER, 
    DEFAULT_SL_PERCENTAGE, 
    DEFAULT_SWING_LOW_PERIOD,
    DEFAULT_RISK_REWARD_TP1,
    DEFAULT_RISK_REWARD_TP2
)

def check_long_signal(df, symbol, timeframe):
    """
    Checks if the conditions for a LONG signal are met.
    If so, calculates SL/TP and returns a structured forecast.

    :param df: DataFrame with OHLCV data and indicators.
    :param symbol: The trading pair symbol.
    :param timeframe: The timeframe for the signal.
    :return: A dictionary representing the forecast, or None.
    """
    if df is None or len(df) < 50:
        # Need at least 50 periods for EMA 50
        return None

    # Get the last two candles for comparison
    last_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]

    # --- Condition Checks ---
    # 1. EMA Trend: EMA12 > EMA50
    ema_trend_ok = last_candle['EMA_12'] > last_candle['EMA_50']

    # 2. EMA Crossover: Price crossed EMA12 from below
    price_crossed_up_ema12 = (prev_candle['close'] < prev_candle['EMA_12']) and \
                             (last_candle['close'] > last_candle['EMA_12'])

    # 3. RSI Filter: RSI is between 40 and 70
    rsi_ok = 40 <= last_candle['RSI_14'] <= 70

    # 4. Volatility Check: ATR is positive
    volatility_ok = last_candle['ATRr_14'] > 0

    # --- Debug Logging ---
    if not (ema_trend_ok and price_crossed_up_ema12 and rsi_ok and volatility_ok):
        print(f"-> No signal for {symbol}. Reason:")
        print(f"   - EMA Trend (12 > 50): {'OK' if ema_trend_ok else 'FAIL'} (EMA12: {last_candle['EMA_12']:.2f}, EMA50: {last_candle['EMA_50']:.2f})")
        print(f"   - EMA Crossover: {'OK' if price_crossed_up_ema12 else 'FAIL'} (Prev Close: {prev_candle['close']:.2f}, Prev EMA12: {prev_candle['EMA_12']:.2f}; Last Close: {last_candle['close']:.2f}, Last EMA12: {last_candle['EMA_12']:.2f})")
        print(f"   - RSI (40-70): {'OK' if rsi_ok else 'FAIL'} (RSI: {last_candle['RSI_14']:.2f})")
        print(f"   - Volatility (ATR > 0): {'OK' if volatility_ok else 'FAIL'} (ATR: {last_candle['ATRr_14']:.4f})")


    # --- Signal Generation ---
    if ema_trend_ok and price_crossed_up_ema12 and rsi_ok and volatility_ok:
        entry_price = last_candle['close']
        
        # --- SL/TP Calculation ---
        stop_loss_price, sl_params = calculate_stop_loss(
            entry_price=entry_price, 
            method=DEFAULT_SL_METHOD, 
            atr=last_candle['ATRr_14'],
            df=df
        )

        take_profit_1, take_profit_2 = calculate_take_profit(
            entry_price=entry_price,
            stop_loss_price=stop_loss_price
        )

        # --- Forecast Structure ---
        forecast = {
            'forecast_id': str(uuid.uuid4()),
            'symbol': symbol,
            'direction': 'LONG',
            'timeframe': timeframe,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'take_profit1_price': take_profit_1,
            'take_profit2_price': take_profit_2,
            'sl_method': sl_params['method'],
            'sl_params': sl_params,
            'created_at': datetime.utcnow(),
            'status': 'open',
            'raw_signal': {
                'ema12': last_candle['EMA_12'],
                'ema50': last_candle['EMA_50'],
                'rsi14': last_candle['RSI_14'],
                'atr14': last_candle['ATRr_14'],
                'close': last_candle['close'],
                'timestamp': last_candle.name
            }
        }
        return forecast
    
    return None

def calculate_stop_loss(entry_price, method, atr, df):
    """Calculates stop-loss based on the selected method."""
    sl_params = {'method': method}
    if method == 'atr':
        k = DEFAULT_ATR_MULTIPLIER
        sl = entry_price - (atr * k)
        sl_params['atr'] = atr
        sl_params['multiplier'] = k
    elif method == 'percentage':
        pct = DEFAULT_SL_PERCENTAGE
        sl = entry_price * (1 - pct)
        sl_params['percentage'] = pct
    elif method == 'swing_low':
        n = DEFAULT_SWING_LOW_PERIOD
        swing_low_df = df.iloc[-n:]
        lowest = swing_low_df['low'].min()
        sl = lowest
        sl_params['period'] = n
        sl_params['lowest_price'] = lowest
    else:
        raise ValueError(f"Unknown stop-loss method: {method}")
        
    return sl, sl_params

def calculate_take_profit(entry_price, stop_loss_price):
    """Calculates take-profit levels based on Risk/Reward ratio."""
    risk = entry_price - stop_loss_price
    tp1 = entry_price + (risk * DEFAULT_RISK_REWARD_TP1)
    tp2 = entry_price + (risk * DEFAULT_RISK_REWARD_TP2)
    return tp1, tp2

if __name__ == '__main__':
    # Example usage:
    from modules.data_fetcher import get_exchange, fetch_ohlcv
    from modules.indicator_calculator import add_indicators
    from config import EXCHANGE_ID, SYMBOLS

    exchange = get_exchange(EXCHANGE_ID)
    if exchange:
        symbol_to_test = 'BTC/USDT'
        print(f"--- Checking for signal on {symbol_to_test} ---")
        
        # Fetch enough data for indicators
        ohlcv_data = fetch_ohlcv(exchange, symbol_to_test, timeframe='1h', limit=200)
        
        if ohlcv_data is not None:
            # Add indicators
            data_with_indicators = add_indicators(ohlcv_data)
            
            # Check for a signal
            signal = check_long_signal(data_with_indicators, symbol_to_test, '1h')
            
            if signal:
                print("✅ Signal Generated!")
                import json
                print(json.dumps(signal, default=str, indent=2))
            else:
                print("❌ No signal found under current conditions.")
