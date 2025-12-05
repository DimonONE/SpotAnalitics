import ccxt
import pandas as pd
from datetime import datetime, timedelta

def get_exchange(exchange_id):
    """Initializes and returns an exchange instance."""
    exchange = getattr(ccxt, exchange_id)()
    return exchange

def fetch_ohlcv(exchange, symbol, timeframe='1h', limit=100):
    """
    Fetches historical OHLCV data for a given symbol and timeframe.

    :param exchange: The ccxt exchange instance.
    :param symbol: The symbol to fetch data for (e.g., 'BTC/USDT').
    :param timeframe: The timeframe to use (e.g., '1h', '4h', '1d').
    :param limit: The number of candles to fetch.
    :return: A pandas DataFrame with OHLCV data, or None if fetching fails.
    """
    try:
        if not exchange.has['fetchOHLCV']:
            print(f"Exchange {exchange.id} does not support fetching OHLCV data.")
            return None

        # Fetch the OHLCV data
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

        if not ohlcv:
            print(f"No data returned for {symbol} on timeframe {timeframe}")
            return None

        # Convert to pandas DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Set timestamp as index
        df.set_index('timestamp', inplace=True)
        
        return df

    except ccxt.NetworkError as e:
        print(f"Network error while fetching {symbol}: {e}")
        return None
    except ccxt.ExchangeError as e:
        print(f"Exchange error while fetching {symbol}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while fetching {symbol}: {e}")
        return None

def get_top_volume_symbols(exchange, n=20):
    """
    Fetches the top N symbols by 24h trading volume in USDT.

    :param exchange: The ccxt exchange instance.
    :param n: The number of top symbols to return.
    :return: A list of symbols, or None.
    """
    try:
        if not exchange.has['fetchTickers']:
            print(f"Exchange {exchange.id} does not support fetching tickers.")
            return None
        
        # Fetch all tickers
        tickers = exchange.fetch_tickers()
        
        # Filter for USDT pairs and sort by 24h volume
        usdt_tickers = {
            symbol: ticker for symbol, ticker in tickers.items()
            if symbol.endswith('/USDT') and ticker.get('quoteVolume') is not None
        }
        
        # Sort by quoteVolume in descending order
        sorted_tickers = sorted(
            usdt_tickers.values(), 
            key=lambda t: t['quoteVolume'], 
            reverse=True
        )
        
        # # Get the top N symbols
        # top_symbols = [ticker['symbol'] for ticker in sorted_tickers[:n]]
        
        # return top_symbols

        return [t["symbol"] for t in sorted_tickers]

    except ccxt.NetworkError as e:
        print(f"Network error while fetching tickers: {e}")
        return None
    except ccxt.ExchangeError as e:
        print(f"Exchange error while fetching tickers: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while fetching tickers: {e}")
        return None

if __name__ == '__main__':
    # Example usage:
    from config import EXCHANGE_ID, TOP_N_COINS_BY_VOLUME
    
    exchange_instance = get_exchange(EXCHANGE_ID)
    
    if exchange_instance:
        print(f"Fetching top {TOP_N_COINS_BY_VOLUME} symbols by volume...")
        top_symbols = get_top_volume_symbols(exchange_instance, TOP_N_COINS_BY_VOLUME)
        if top_symbols:
            print("Top symbols found:", top_symbols)
            
            # Test fetching OHLCV for the top symbol
            if top_symbols:
                top_sym = top_symbols[0]
                print(f"\nFetching data for top symbol: {top_sym}...")
                data = fetch_ohlcv(exchange_instance, top_sym, timeframe='1h', limit=5)
                if data is not None:
                    print(data)
        else:
            print("Could not fetch top symbols.")
