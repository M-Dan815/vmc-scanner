# test_signals.py
# ─────────────────────────────────────────────────────────────────────────────
# Validation script — three signal types only.
# Usage:
#   python test_signals.py
#   python test_signals.py --symbol BTCUSDT --tf 1w
#   python test_signals.py --symbol FLR-USD --tf 1d --type coinbase
#   python test_signals.py --all
# ─────────────────────────────────────────────────────────────────────────────

import argparse
import logging

logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

from fetcher       import fetch_ohlcv
from signal_engine import (
    calculate_wavetrend,
    detect_signals,
    get_all_historical_signals,
    get_latest_signal,
)
from scanner import load_watchlist, BUY_TIMEFRAMES, SELL_TIMEFRAMES
import config

SEPARATOR = '─' * 62

SIGNAL_EMOJI = {
    'BIG_GREEN':  '🟢',
    'BIG_RED':    '🔴',
    'YELLOW_BUY': '🟡',
    'UNKNOWN':    '⚪',
}


def test_single(symbol: str, timeframe: str, asset_type: str = 'crypto'):
    print(f"\n{SEPARATOR}")
    print(f"  {symbol}  |  {config.TIMEFRAME_LABELS.get(timeframe, timeframe)}")
    print(SEPARATOR)

    df = fetch_ohlcv(symbol, timeframe, asset_type=asset_type)
    if df is None:
        print(f"  ERROR: Could not fetch data for {symbol} {timeframe}")
        return

    df = calculate_wavetrend(df)
    df = detect_signals(df)

    print("\n  Last 10 candles:\n")
    display = df[[
        'timestamp', 'close', 'wt1', 'wt2',
        'big_green', 'big_red', 'yellow_buy'
    ]].tail(10).copy()

    display['wt1']   = display['wt1'].round(4)
    display['wt2']   = display['wt2'].round(4)
    display['close'] = display['close'].round(4)

    def label_signal(r):
        if r['big_green']:  return '🟢 BIG GREEN'
        if r['big_red']:    return '🔴 BIG RED'
        if r['yellow_buy']: return '🟡 YELLOW BUY'
        return '·'

    display['signal'] = display.apply(label_signal, axis=1)
    display = display[['timestamp', 'close', 'wt1', 'wt2', 'signal']]
    print(display.to_string(index=False))

    historical = get_all_historical_signals(df)
    if not historical.empty:
        print(f"\n  Last {min(5, len(historical))} historical signals:\n")
        for _, row in historical.tail(5).iterrows():
            emoji = SIGNAL_EMOJI.get(row['signal_type'], '⚪')
            print(
                f"    {emoji} {row['signal_type']:13s} | "
                f"{str(row['timestamp'])[:19]} | "
                f"WT1={row['wt1']:.4f} | "
                f"Close={row['close']:.4f}"
            )
    else:
        print("\n  No historical signals found in dataset.")

    current = get_latest_signal(df)
    print()
    if current:
        emoji     = SIGNAL_EMOJI.get(current['signal_type'], '⚪')
        direction = current.get('direction', '')
        allowed   = (
            (direction == 'BUY'  and timeframe in BUY_TIMEFRAMES) or
            (direction == 'SELL' and timeframe in SELL_TIMEFRAMES)
        )
        tf_status = "✅ fires on this timeframe" if allowed else "🚫 filtered on this timeframe"
        print(
            f"  LIVE SIGNAL: {emoji} {current['signal_type']} | "
            f"WT1={current['wt1']} | {tf_status}"
        )
    else:
        print("  No signal on last closed bar.")
    print()


def _print_asset_status(asset: dict, timeframe: str):
    symbol     = asset['symbol']
    asset_type = asset['asset_type']
    df         = fetch_ohlcv(symbol, timeframe, asset_type=asset_type)

    if df is None or len(df) < 50:
        print(f"    {symbol:15s} → ⚠  No data")
        return

    df       = calculate_wavetrend(df)
    df       = detect_signals(df)
    signal   = get_latest_signal(df)
    last_wt1 = round(float(df['wt1'].iloc[-2]), 2)

    if signal:
        emoji     = SIGNAL_EMOJI.get(signal['signal_type'], '⚪')
        direction = signal.get('direction', '')
        allowed   = (
            (direction == 'BUY'  and timeframe in BUY_TIMEFRAMES) or
            (direction == 'SELL' and timeframe in SELL_TIMEFRAMES)
        )
        tf_note = '' if allowed else ' 🚫 filtered'
        status  = f"{emoji} {signal['signal_type']}{tf_note}"
    else:
        status = f"  · (WT1={last_wt1})"

    print(f"    {symbol:15s} → {status}")


def test_all_watchlist():
    assets   = load_watchlist()
    holdings = [a for a in assets if a['group'] == 'holdings']
    watching = [a for a in assets if a['group'] == 'keep_an_eye']

    for timeframe in config.TIMEFRAMES:
        tf_label = config.TIMEFRAME_LABELS.get(timeframe, timeframe)
        print(f"\n{'=' * 62}")
        print(f"  {tf_label} Scan")
        print(f"  BUY fires on: {BUY_TIMEFRAMES} | SELL fires on: {SELL_TIMEFRAMES}")
        print(f"{'=' * 62}")

        if holdings:
            print(f"\n  🚨 HOLDINGS ({len(holdings)}):")
            for asset in holdings:
                _print_asset_status(asset, timeframe)

        if watching:
            print(f"\n  👀 KEEP AN EYE ({len(watching)}):")
            for asset in watching:
                _print_asset_status(asset, timeframe)

    print()


def main():
    parser = argparse.ArgumentParser(description='VMC Cipher B Signal Validator')
    parser.add_argument('--symbol',  default='BTCUSDT', help='Asset symbol')
    parser.add_argument(
        '--tf', default='1w',
        choices=['4h', '1d', '1w', '1M'],
        help='Timeframe'
    )
    parser.add_argument(
        '--type', default='crypto',
        choices=['crypto', 'coinbase', 'stock'],
        dest='asset_type',
        help='Asset type'
    )
    parser.add_argument(
        '--all', action='store_true',
        help='Test all watchlist assets across all timeframes'
    )
    args = parser.parse_args()

    if args.all:
        test_all_watchlist()
    else:
        test_single(args.symbol, args.tf, args.asset_type)


if __name__ == '__main__':
    main()