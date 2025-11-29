# Telegram Bot Token
# Replace "YOUR_TELEGRAM_BOT_TOKEN" with your actual bot token from BotFather
TELEGRAM_BOT_TOKEN = "1158077877:AAGyoJ1zo0JHQZ5s89UJMCnSZTZ-Ns3wueM"

# Exchange settings
# Using Binance as default, no API key needed for public data
EXCHANGE_ID = 'binance'

# Number of top coins by volume to track
TOP_N_COINS_BY_VOLUME = 20

# Default user settings
# These can be overridden by user profiles later
DEFAULT_TIMEFRAME = '1m'
DEFAULT_SL_METHOD = 'atr'  # atr, percentage, swing_low
DEFAULT_ATR_MULTIPLIER = 1.5
DEFAULT_SL_PERCENTAGE = 0.03 # 3%
DEFAULT_SWING_LOW_PERIOD = 14 # Last 14 candles
DEFAULT_RISK_REWARD_TP1 = 1.5
DEFAULT_RISK_REWARD_TP2 = 3.0
