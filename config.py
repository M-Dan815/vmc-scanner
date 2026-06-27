# config.py
# ─────────────────────────────────────────────────────────────────────────────
# Central configuration for VMC Cipher B Alert Scanner
# ─────────────────────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# CRYPTO WATCHLIST (fallback if watchlist.json not found)
# ─────────────────────────────────────────────────────────────────────────────
CRYPTO_WATCHLIST = [
    "ADAUSDT", "AVAXUSDT", "SOLUSDT", "ETHUSDT", "LINKUSDT",
    "SUIUSDT", "XRPUSDT", "UNIUSDT", "DOGEUSDT", "ALGOUSDT",
    "WIFUSDT", "SUSHIUSDT", "PEPEUSDT", "AAVEUSDT", "XLMUSDT",
    "HBARUSDT", "BTCUSDT",
]

# ─────────────────────────────────────────────────────────────────────────────
# STOCK WATCHLIST (Phase 2)
# ─────────────────────────────────────────────────────────────────────────────
STOCK_WATCHLIST = [
    "ADSK", "META", "ADBE", "TSLA", "CRM", "COIN",
    "AAPL", "NVDA", "AMD", "INTC", "IBM", "PYPL",
]

# ─────────────────────────────────────────────────────────────────────────────
# ACTIVE MODES
# ─────────────────────────────────────────────────────────────────────────────
ENABLE_CRYPTO = os.getenv("ENABLE_CRYPTO", "true").lower() == "true"
ENABLE_STOCKS = os.getenv("ENABLE_STOCKS", "false").lower() == "true"

# ─────────────────────────────────────────────────────────────────────────────
# TIMEFRAMES
# ─────────────────────────────────────────────────────────────────────────────
TIMEFRAMES = ['4h', '1d', '1w', '1M']

TIMEFRAME_LABELS = {
    '4h': '4-Hour',
    '1d': 'Daily',
    '1w': 'Weekly',
    '1M': 'Monthly',
}

# ─────────────────────────────────────────────────────────────────────────────
# VMC CIPHER B PARAMETERS
# WT / OS values: DO NOT CHANGE — affects signal logic
# RED_LEVEL changed from +60 to +40 per Shantnu request
# ─────────────────────────────────────────────────────────────────────────────
WT_CHANNEL_LEN = int(os.getenv("WT_CHANNEL_LEN", "9"))
WT_AVERAGE_LEN = int(os.getenv("WT_AVERAGE_LEN", "12"))
WT_MA_LEN      = int(os.getenv("WT_MA_LEN", "3"))
OS_LEVEL       = float(os.getenv("OS_LEVEL", "-60.0"))   # Big Green threshold
RED_LEVEL      = float(os.getenv("RED_LEVEL", "40.0"))   # Big Red threshold

# ─────────────────────────────────────────────────────────────────────────────
# DATA SOURCES
# ─────────────────────────────────────────────────────────────────────────────
BINANCE_BASE_URL  = os.getenv("BINANCE_BASE_URL", "https://api.binance.us")
BINANCE_KLINES    = "/api/v3/klines"
COINBASE_BASE_URL = "https://api.exchange.coinbase.com"
YAHOO_FINANCE_ENABLED = False
CANDLE_LIMIT = 300

# ─────────────────────────────────────────────────────────────────────────────
# GMAIL CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
GMAIL_SENDER    = os.getenv("GMAIL_SENDER", "")
GMAIL_APP_PASS  = os.getenv("GMAIL_APP_PASS", "")
GMAIL_RECIPIENT = os.getenv("GMAIL_RECIPIENT", "jn.shantnu@gmail.com")

# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULER TIMING (UTC)
# ─────────────────────────────────────────────────────────────────────────────
SCAN_4H_MINUTE  = 3
SCAN_1D_HOUR    = 0
SCAN_1D_MINUTE  = 5
SCAN_1W_DOW     = 'mon'
SCAN_1W_HOUR    = 0
SCAN_1W_MINUTE  = 10
SCAN_1M_DAY     = 1
SCAN_1M_HOUR    = 0
SCAN_1M_MINUTE  = 15

# ─────────────────────────────────────────────────────────────────────────────
# API RATE LIMITING
# ─────────────────────────────────────────────────────────────────────────────
REQUEST_DELAY_SECONDS = 0.2
MAX_RETRIES           = 3
RETRY_DELAY_SECONDS   = 5.0

# ─────────────────────────────────────────────────────────────────────────────
# DEDUPLICATION
# ─────────────────────────────────────────────────────────────────────────────
ALERT_HISTORY_FILE  = "data/alert_history.json"
MAX_HISTORY_ENTRIES = 5000

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
LOG_FILE         = "logs/scanner.log"
LOG_LEVEL        = os.getenv("LOG_LEVEL", "INFO")
LOG_MAX_BYTES    = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3