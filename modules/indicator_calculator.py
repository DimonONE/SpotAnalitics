import pandas_ta as ta

def add_indicators(df):
    """
    Calculates and adds technical indicators to the DataFrame.

    :param df: A pandas DataFrame with OHLCV data.
    :return: The DataFrame with added indicator columns.
    """
    if df is None or df.empty:
        return df

    # Calculate EMA (Exponential Moving Average)
    df.ta.ema(length=12, append=True)
    df.ta.ema(length=50, append=True)

    # Calculate RSI (Relative Strength Index)
    df.ta.rsi(length=14, append=True)

    # Calculate ATR (Average True Range)
    df.ta.atr(length=14, append=True)

    return df

if __name__ == '__main__':
    # Example usage:
    # This requires the data_fetcher to work
    from config import EXCHANGE_ID, SYMBOLS
    from modules.data_fetcher import get_exchange, fetch_ohlcv

    exchange_instance = get_exchange(EXCHANGE_ID)
    if exchange_instance:
        symbol = SYMBOLS[0]
        print(f"Fetching data for {symbol} to test indicators...")
        
        # Fetch a larger dataset for accurate indicator calculation
        data = fetch_ohlcv(exchange_instance, symbol, timeframe='1h', limit=200)
        
        if data is not None:
            # Add indicators
            data_with_indicators = add_indicators(data)
            
            # Print the last 5 rows with the new indicators
            print(data_with_indicators.tail())

