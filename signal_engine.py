# signal_engine.py
# ─────────────────────────────────────────────────────────────────────────────
# WaveTrend logic for VMC Cipher B
#
# Signal logic (final):
#   BIG_GREEN  → bullish crossover with WT1 < -60
#   BIG_RED    → ANY bearish crossover regardless of zone
#   YELLOW_BUY → bullish crossover with WT1 between -60 and +40
#
# No other signal types exist in this system.
# ─────────────────────────────────────────────────────────────────────────────

import logging
import numpy  as np
import pandas as pd

import config

logger = logging.getLogger(__name__)


def _ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def _sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(window=length).mean()


def calculate_wavetrend(
    df: pd.DataFrame,
    wt_channel_len: int = config.WT_CHANNEL_LEN,
    wt_average_len: int = config.WT_AVERAGE_LEN,
    wt_ma_len:      int = config.WT_MA_LEN,
) -> pd.DataFrame:
    """
    Replicates the full WaveTrend oscillator from VMC Cipher B.

    Pine Script:
        esa  = ema(hlc3, wtChannelLen)
        d    = ema(abs(hlc3 - esa), wtChannelLen)
        ci   = (hlc3 - esa) / (0.015 * d)
        wt1  = ema(ci, wtAverageLen)
        wt2  = sma(wt1, wtMALen)
    """
    df = df.copy()

    hlc3 = (df['high'] + df['low'] + df['close']) / 3
    esa  = _ema(hlc3, wt_channel_len)
    d    = _ema(abs(hlc3 - esa), wt_channel_len)
    ci   = (hlc3 - esa) / (0.015 * d.replace(0, np.nan))
    wt1  = _ema(ci, wt_average_len)
    wt2  = _sma(wt1, wt_ma_len)

    df['wt1'] = wt1
    df['wt2'] = wt2

    logger.debug(
        f"WaveTrend calculated. "
        f"Last WT1={round(float(wt1.iloc[-1]), 4) if not wt1.empty else 'N/A'}, "
        f"Last WT2={round(float(wt2.iloc[-1]), 4) if not wt2.empty else 'N/A'}"
    )
    return df


def detect_signals(
    df: pd.DataFrame,
    os_level:  float = config.OS_LEVEL,
    red_level: float = config.RED_LEVEL,
) -> pd.DataFrame:
    """
    Three signals only:

    Bullish crossover (wt2 crosses above wt1):
      WT1 < os_level (-60)               → big_green
      os_level <= WT1 <= red_level (+40) → yellow_buy

    Bearish crossover (wt2 crosses below wt1):
      ANY zone                           → big_red
    """
    df = df.copy()

    wt1_curr = df['wt1']
    wt2_curr = df['wt2']
    wt1_prev = df['wt1'].shift(1)
    wt2_prev = df['wt2'].shift(1)

    # ── Crossover detection ───────────────────────────────────────────────
    cross_above = (wt2_prev < wt1_prev) & (wt2_curr >= wt1_curr)
    cross_below = (wt2_prev > wt1_prev) & (wt2_curr <= wt1_curr)

    # ── Zone detection ────────────────────────────────────────────────────
    in_green_zone  = wt1_curr < os_level
    in_middle_zone = (wt1_curr >= os_level) & (wt1_curr <= red_level)

    # ── Signal assignment ─────────────────────────────────────────────────
    df['big_green']  = cross_above & in_green_zone
    df['yellow_buy'] = cross_above & in_middle_zone
    df['big_red']    = cross_below   # ALL bearish crossovers

    logger.debug(
        f"Signals detected over {len(df)} candles → "
        f"Big Green: {int(df['big_green'].sum())} | "
        f"Big Red: {int(df['big_red'].sum())} | "
        f"Yellow Buy: {int(df['yellow_buy'].sum())}"
    )
    return df


def get_latest_signal(df: pd.DataFrame) -> dict | None:
    """
    Returns the signal on the most recently CLOSED candle (index -2).

    Priority:
        1. BIG_GREEN   — strongest bullish
        2. BIG_RED     — all bearish
        3. YELLOW_BUY  — moderate bullish

    Returns None if no signal on the last closed candle.
    """
    if len(df) < 3:
        logger.warning("Not enough candles to determine signal safely.")
        return None

    last_closed = df.iloc[-2]

    if pd.isna(last_closed['wt1']) or pd.isna(last_closed['wt2']):
        logger.warning("NaN in WaveTrend on last closed candle. Skipping.")
        return None

    wt1 = round(float(last_closed['wt1']), 4)
    wt2 = round(float(last_closed['wt2']), 4)
    ts  = last_closed['timestamp']

    if bool(last_closed['big_green']):
        return {
            'signal_type':  'BIG_GREEN',
            'signal_label': 'Big Green Dot — BUY',
            'direction':    'BUY',
            'wt1': wt1, 'wt2': wt2, 'timestamp': ts,
        }

    if bool(last_closed['big_red']):
        return {
            'signal_type':  'BIG_RED',
            'signal_label': 'Big Red Dot — SELL',
            'direction':    'SELL',
            'wt1': wt1, 'wt2': wt2, 'timestamp': ts,
        }

    if bool(last_closed['yellow_buy']):
        return {
            'signal_type':  'YELLOW_BUY',
            'signal_label': 'Yellow — BUY',
            'direction':    'BUY',
            'wt1': wt1, 'wt2': wt2, 'timestamp': ts,
        }

    return None


def get_all_historical_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns all historical signals in the DataFrame.
    Used during validation to compare against TradingView chart history.
    """
    mask = (
        df['big_green'] |
        df['big_red'] |
        df['yellow_buy']
    )
    signals = df[mask].copy()

    def classify(row):
        if row['big_green']:  return 'BIG_GREEN'
        if row['big_red']:    return 'BIG_RED'
        if row['yellow_buy']: return 'YELLOW_BUY'
        return 'UNKNOWN'

    signals['signal_type'] = signals.apply(classify, axis=1)
    return signals[['timestamp', 'close', 'wt1', 'wt2', 'signal_type']].copy()