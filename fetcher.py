# fetcher.py
# ─────────────────────────────────────────────────────────────────────────────
# Fetches OHLCV data from Binance.US, Coinbase, or Yahoo Finance.
# Coinbase assets with limited granularity support are handled gracefully.
# ─────────────────────────────────────────────────────────────────────────────

import time
import logging
import requests
import pandas as pd

import config

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# BINANCE
# ─────────────────────────────────────────────────────────────────────────────

BINANCE_INTERVAL_MAP = {
    '4h': '4h',
    '1d': '1d',
    '1w': '1w',
    '1M': '1M',
}


def fetch_binance_ohlcv(
    symbol: str,
    timeframe: str,
    limit: int = config.CANDLE_LIMIT
) -> pd.DataFrame:
    if timeframe not in BINANCE_INTERVAL_MAP:
        raise ValueError(
            f"Unsupported timeframe '{timeframe}'. "
            f"Supported: {list(BINANCE_INTERVAL_MAP.keys())}"
        )

    interval = BINANCE_INTERVAL_MAP[timeframe]
    url      = f"{config.BINANCE_BASE_URL}{config.BINANCE_KLINES}"

    params = {
        'symbol':   symbol.upper(),
        'interval': interval,
        'limit':    limit,
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        raw = response.json()
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Binance API timeout for {symbol} {timeframe}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Binance API connection error for {symbol} {timeframe}")
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(
            f"Binance API HTTP {response.status_code} for {symbol} {timeframe}: {exc}"
        )

    if isinstance(raw, dict):
        code = raw.get('code', 'unknown')
        msg  = raw.get('msg', 'unknown error')
        raise RuntimeError(
            f"Binance API error for {symbol} {timeframe}: code={code}, msg={msg}"
        )

    if not raw:
        raise RuntimeError(f"Binance returned empty data for {symbol} {timeframe}")

    df = pd.DataFrame(raw, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'num_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore',
    ])

    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms', utc=True)
    df['open']      = df['open'].astype(float)
    df['high']      = df['high'].astype(float)
    df['low']       = df['low'].astype(float)
    df['close']     = df['close'].astype(float)
    df['volume']    = df['volume'].astype(float)

    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
    df = df.sort_values('timestamp').reset_index(drop=True)

    logger.debug(f"Binance: fetched {len(df)} candles for {symbol} {timeframe}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# COINBASE
# ─────────────────────────────────────────────────────────────────────────────

COINBASE_INTERVAL_MAP = {
    '4h':  14400,
    '1d':  86400,
    '1w':  604800,
    '1M':  2592000,
}

# Assets confirmed to only support specific timeframes on Coinbase.
# Verified by live API testing June 2026.
COINBASE_SUPPORTED_TIMEFRAMES = {
    'AERO-USD': {'1d'},
    'FLR-USD':  {'1d'},
}


def fetch_coinbase_ohlcv(
    symbol: str,
    timeframe: str,
    limit: int = config.CANDLE_LIMIT
) -> pd.DataFrame:
    # ── Graceful skip for unsupported timeframes ──────────────────────────
    if symbol in COINBASE_SUPPORTED_TIMEFRAMES:
        if timeframe not in COINBASE_SUPPORTED_TIMEFRAMES[symbol]:
            supported = COINBASE_SUPPORTED_TIMEFRAMES[symbol]
            raise RuntimeError(
                f"Coinbase does not support {timeframe} for {symbol}. "
                f"Supported timeframes: {supported}. Skipping gracefully."
            )

    if timeframe not in COINBASE_INTERVAL_MAP:
        raise ValueError(
            f"Unsupported timeframe '{timeframe}' for Coinbase."
        )

    granularity = COINBASE_INTERVAL_MAP[timeframe]
    url         = f"{config.COINBASE_BASE_URL}/products/{symbol}/candles"

    params = {'granularity': granularity}

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        raw = response.json()
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Coinbase API timeout for {symbol} {timeframe}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Coinbase API connection error for {symbol} {timeframe}")
    except requests.exceptions.HTTPError as exc:
        raise RuntimeError(
            f"Coinbase API HTTP {response.status_code} "
            f"for {symbol} {timeframe}: {exc}"
        )

    if not raw:
        raise RuntimeError(f"Coinbase returned empty data for {symbol} {timeframe}")

    # Coinbase format: [timestamp, low, high, open, close, volume]
    df = pd.DataFrame(raw, columns=[
        'timestamp', 'low', 'high', 'open', 'close', 'volume'
    ])

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True)
    df['open']      = df['open'].astype(float)
    df['high']      = df['high'].astype(float)
    df['low']       = df['low'].astype(float)
    df['close']     = df['close'].astype(float)
    df['volume']    = df['volume'].astype(float)

    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
    df = df.sort_values('timestamp').reset_index(drop=True)

    if len(df) > limit:
        df = df.tail(limit).reset_index(drop=True)

    logger.debug(f"Coinbase: fetched {len(df)} candles for {symbol} {timeframe}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# YAHOO FINANCE (Phase 2 stub)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_yahoo_ohlcv(
    symbol: str,
    timeframe: str,
    limit: int = config.CANDLE_LIMIT
) -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError:
        raise RuntimeError("yfinance not installed. Run: pip install yfinance")

    yf_map = {
        '4h': ('60m', '60d'),
        '1d': ('1d',  '2y'),
        '1w': ('1wk', '5y'),
        '1M': ('1mo', '10y'),
    }

    if timeframe not in yf_map:
        raise ValueError(f"Unsupported timeframe '{timeframe}' for Yahoo Finance.")

    interval, period = yf_map[timeframe]
    ticker = yf.Ticker(symbol)
    raw    = ticker.history(interval=interval, period=period)

    if raw is None or raw.empty:
        raise RuntimeError(f"Yahoo Finance returned no data for {symbol} {timeframe}.")

    df = raw.reset_index()
    df.columns = [c.lower() for c in df.columns]

    time_col = 'datetime' if 'datetime' in df.columns else 'date'
    df['timestamp'] = pd.to_datetime(df[time_col], utc=True)

    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
    df = df.sort_values('timestamp').reset_index(drop=True)

    if len(df) > limit:
        df = df.tail(limit).reset_index(drop=True)

    logger.debug(f"Yahoo Finance: fetched {len(df)} candles for {symbol} {timeframe}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# UNIFIED FETCHER WITH RETRY
# ─────────────────────────────────────────────────────────────────────────────

def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    asset_type: str = 'crypto',
    limit: int = config.CANDLE_LIMIT
) -> pd.DataFrame | None:
    """
    Unified fetcher with retry logic.
    Routes to Binance.US (crypto), Coinbase, or Yahoo Finance (stocks).
    Unsupported Coinbase timeframes are skipped cleanly without retrying.
    """
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            if asset_type == 'coinbase':
                df = fetch_coinbase_ohlcv(symbol, timeframe, limit)
            elif asset_type == 'crypto':
                df = fetch_binance_ohlcv(symbol, timeframe, limit)
            elif asset_type == 'stock':
                df = fetch_yahoo_ohlcv(symbol, timeframe, limit)
            else:
                raise ValueError(f"Unknown asset_type '{asset_type}'")

            if len(df) < 50:
                logger.warning(
                    f"Only {len(df)} candles for {symbol} {timeframe}. "
                    f"EMA accuracy may be reduced."
                )
            return df

        except RuntimeError as exc:
            # Clean skip — no retry for known unsupported timeframes
            if "does not support" in str(exc):
                logger.info(
                    f"Skipping {symbol} {timeframe} — "
                    f"timeframe not supported on Coinbase for this asset."
                )
                return None

            logger.warning(
                f"Fetch attempt {attempt}/{config.MAX_RETRIES} "
                f"failed for {symbol} {timeframe}: {exc}"
            )
            if attempt < config.MAX_RETRIES:
                time.sleep(config.RETRY_DELAY_SECONDS)

        except Exception as exc:
            logger.error(
                f"Unexpected error fetching {symbol} {timeframe}: {exc}",
                exc_info=True
            )
            break

    logger.error(
        f"All {config.MAX_RETRIES} retries exhausted for "
        f"{symbol} {timeframe}. Skipping."
    )
    return None