# ─────────────────────────────────────────────────────────────────────────────
# scanner.py
# ─────────────────────────────────────────────────────────────────────────────
# Orchestrates: Load watchlist → Fetch → Calculate → Detect → Alert
#
# Timeframe filters (final):
#   BUY signals  (BIG_GREEN, YELLOW_BUY) → Weekly (1w), Monthly (1M) only
#   SELL signals (BIG_RED)               → 4H (4h), Daily (1d), Weekly (1w) only
#
# Big Red zone enforcement (WT1 > +40) is handled inside signal_engine.py.
# No additional WT1 threshold check is needed here.
#
# CHANGE (consolidation): Alerts are no longer emailed one-by-one as they're
# detected. Instead, all non-duplicate signals found during a single
# scan_timeframe() pass are grouped by signal_type (BIG_GREEN / BIG_RED /
# YELLOW_BUY) and sent as ONE consolidated email per type at the end of
# the pass — e.g. one email listing every Big Red hit for that scan.
# ─────────────────────────────────────────────────────────────────────────────
import json
import time
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import config
from fetcher import fetch_ohlcv
from signal_engine import calculate_wavetrend, detect_signals, get_latest_signal
from alert_manager import AlertManager

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# TIMEFRAME FILTERS
# ─────────────────────────────────────────────────────────────────────────────
BUY_TIMEFRAMES = {'1w', '1M'}
SELL_TIMEFRAMES = {'4h', '1d', '1w'}

# Signal types that get consolidated (all three currently do).
CONSOLIDATED_SIGNAL_TYPES = ['BIG_GREEN', 'BIG_RED', 'YELLOW_BUY']


def load_watchlist(filepath: str = 'watchlist.json') -> list[dict]:
    """
    Loads active assets from watchlist.json.
    Falls back to config.py CRYPTO_WATCHLIST if file not found.
    """
    wl_path = Path(filepath)
    if not wl_path.exists():
        logger.warning(
            f"watchlist.json not found. "
            f"Falling back to config.py CRYPTO_WATCHLIST."
        )
        return [
            {
                'symbol': s,
                'label': s,
                'asset_type': 'crypto',
                'group': 'keep_an_eye',
            }
            for s in config.CRYPTO_WATCHLIST
        ]

    with open(wl_path, 'r') as f:
        data = json.load(f)

    assets = []

    if config.ENABLE_CRYPTO:
        for entry in data.get('holdings', []):
            if entry.get('active', False):
                assets.append({
                    'symbol':     entry['symbol'],
                    'label':      entry.get('label', entry['symbol']),
                    'asset_type': entry.get('asset_type', 'crypto'),
                    'group':      'holdings',
                })

        for entry in data.get('keep_an_eye', []):
            if entry.get('active', False):
                assets.append({
                    'symbol':     entry['symbol'],
                    'label':      entry.get('label', entry['symbol']),
                    'asset_type': entry.get('asset_type', 'crypto'),
                    'group':      'keep_an_eye',
                })

    if config.ENABLE_STOCKS:
        for entry in data.get('stocks', []):
            if entry.get('active', False):
                assets.append({
                    'symbol':     entry['symbol'],
                    'label':      entry.get('label', entry['symbol']),
                    'asset_type': entry.get('asset_type', 'stock'),
                    'group':      'keep_an_eye',
                })

    seen   = set()
    unique = []
    for asset in assets:
        if asset['symbol'] not in seen:
            seen.add(asset['symbol'])
            unique.append(asset)

    holdings_count = sum(1 for a in unique if a['group'] == 'holdings')
    watch_count    = sum(1 for a in unique if a['group'] == 'keep_an_eye')

    logger.info(
        f"Watchlist loaded: {len(unique)} active assets "
        f"({holdings_count} holdings, {watch_count} keep an eye)"
    )
    return unique


def _is_signal_allowed_on_timeframe(signal: dict, timeframe: str) -> bool:
    """
    Enforces timeframe filtering per signal direction.

    BUY  signals → Weekly (1w) and Monthly (1M) only
    SELL signals → 4H (4h), Daily (1d), Weekly (1w) only

    Note: Big Red's WT1 > +40 zone requirement is enforced in
    signal_engine.detect_signals(), not here.

    Returns True if signal should fire, False if suppressed.
    """
    direction = signal.get('direction', '')

    if direction == 'BUY' and timeframe not in BUY_TIMEFRAMES:
        logger.debug(
            f"BUY signal suppressed on {timeframe} — "
            f"only fires on {BUY_TIMEFRAMES}"
        )
        return False

    if direction == 'SELL' and timeframe not in SELL_TIMEFRAMES:
        logger.debug(
            f"SELL signal suppressed on {timeframe} — "
            f"only fires on {SELL_TIMEFRAMES}"
        )
        return False

    return True


class VMCScanner:

    def __init__(self):
        self.alert_manager = AlertManager()
        self.watchlist     = load_watchlist()

        logger.info(
            f"VMCScanner ready. "
            f"Assets: {len(self.watchlist)} | "
            f"Timeframes: {config.TIMEFRAMES}"
        )
        logger.info(
            f"Timeframe filters → "
            f"BUY: {BUY_TIMEFRAMES} | "
            f"SELL: {SELL_TIMEFRAMES}"
        )

    def reload_watchlist(self):
        self.watchlist = load_watchlist()
        logger.info(f"Watchlist reloaded: {len(self.watchlist)} active assets.")

    def scan_asset(self, asset: dict, timeframe: str, scan_time_dt: datetime) -> dict | None:
        """
        Full pipeline for one asset + timeframe.
        Returns enriched signal dict or None if no signal or filtered out.
        """
        symbol     = asset['symbol']
        label      = asset['label']
        asset_type = asset['asset_type']
        group      = asset['group']

        # ── 1. Fetch OHLCV ────────────────────────────────────────────────
        df = fetch_ohlcv(symbol, timeframe, asset_type=asset_type)

        if df is None:
            return None

        if len(df) < 50:
            logger.warning(
                f"Only {len(df)} candles for {symbol} {timeframe}. Skipping."
            )
            return None

        # ── 2. Calculate WaveTrend ────────────────────────────────────────
        df = calculate_wavetrend(df)

        # ── 3. Detect signals ─────────────────────────────────────────────
        df = detect_signals(df)

        # ── 4. Get signal on last closed candle ───────────────────────────
        signal = get_latest_signal(df)

        if signal is None:
            logger.debug(f"No signal: {symbol} {timeframe}")
            return None

        # ── 5. Apply timeframe filter ─────────────────────────────────────
        if not _is_signal_allowed_on_timeframe(signal, timeframe):
            return None

        # ── 6. Enrich signal ──────────────────────────────────────────────
        signal['symbol']       = symbol
        signal['label']        = label
        signal['asset_type']   = asset_type
        signal['group']        = group
        signal['timeframe']    = timeframe
        signal['tf_label']     = config.TIMEFRAME_LABELS.get(timeframe, timeframe)
        # scan_time: same datetime for every asset in this scan pass, so
        # all signals grouped into one consolidated email share one
        # scan time (both UTC and PT are derived from scan_time_dt).
        signal['scan_time']    = scan_time_dt.strftime('%Y-%m-%d %H:%M UTC')
        signal['scan_time_dt'] = scan_time_dt

        logger.info(
            f"Signal → {symbol} | {group} | {timeframe} | "
            f"{signal['signal_type']} | WT1={signal['wt1']}"
        )
        return signal

    def scan_timeframe(self, timeframe: str) -> list[dict]:
        """
        Scans all active watchlist assets on the given timeframe.
        Collects non-duplicate signals grouped by signal_type, then sends
        ONE consolidated Gmail alert per signal_type (e.g. one email for
        all Big Red hits, one for all Big Green hits, one for all
        Yellow-BUY hits) rather than one email per signal.
        """
        tf_label = config.TIMEFRAME_LABELS.get(timeframe, timeframe)
        logger.info(
            f"─── Starting {tf_label} scan "
            f"({len(self.watchlist)} assets) ───"
        )

        # Single scan_time shared by every signal detected in this pass.
        scan_time_dt = datetime.now(timezone.utc)

        signals_by_type: dict[str, list[dict]] = defaultdict(list)
        skipped = 0
        errors  = 0

        for asset in self.watchlist:
            try:
                signal = self.scan_asset(asset, timeframe, scan_time_dt)

                if signal is None:
                    skipped += 1
                    time.sleep(config.REQUEST_DELAY_SECONDS)
                    continue

                if self.alert_manager.is_duplicate(signal):
                    logger.info(
                        f"Duplicate suppressed: {asset['symbol']} "
                        f"{timeframe} {signal['signal_type']}"
                    )
                    skipped += 1
                    time.sleep(config.REQUEST_DELAY_SECONDS)
                    continue

                signals_by_type[signal['signal_type']].append(signal)

            except Exception as exc:
                logger.error(
                    f"Unhandled error scanning {asset['symbol']} "
                    f"{timeframe}: {exc}",
                    exc_info=True
                )
                errors += 1

            time.sleep(config.REQUEST_DELAY_SECONDS)

        # ── Send one consolidated email per signal type ────────────────────
        alerted: list[dict] = []
        for signal_type in CONSOLIDATED_SIGNAL_TYPES:
            batch = signals_by_type.get(signal_type, [])
            if not batch:
                continue

            success = self.alert_manager.send_consolidated_alert(signal_type, batch)

            if success:
                for signal in batch:
                    self.alert_manager.record_alert(signal)
                alerted.extend(batch)
            else:
                errors += 1
                logger.error(
                    f"Failed to send consolidated {signal_type} alert "
                    f"({len(batch)} signal(s)) for {timeframe}."
                )

        logger.info(
            f"─── {tf_label} scan complete. "
            f"Alerted: {len(alerted)} | "
            f"Skipped: {skipped} | "
            f"Errors: {errors} ───"
        )
        return alerted

    def scan_all(self) -> dict[str, list[dict]]:
        """Scans all configured timeframes. Useful for manual full-scan."""
        logger.info("=== Full scan across all timeframes starting ===")
        results = {}
        for tf in config.TIMEFRAMES:
            results[tf] = self.scan_timeframe(tf)
        logger.info("=== Full scan complete ===")
        return results