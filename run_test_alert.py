# run_test_alert.py
# ─────────────────────────────────────────────────────────────────────────────
# Sends one test alert for each of the 3 signal types.
# Confirms UTC + PT timestamps and group labels are correct.
# ─────────────────────────────────────────────────────────────────────────────

from alert_manager import AlertManager
from datetime import datetime, timezone

manager = AlertManager()
now     = datetime.now(timezone.utc)
now_str = now.strftime('%Y-%m-%d %H:%M UTC')

test_signals = [
    {
        'symbol':       'ALGOUSDT',
        'label':        'Algorand',
        'asset_type':   'crypto',
        'group':        'holdings',
        'timeframe':    '1w',
        'tf_label':     'Weekly',
        'signal_type':  'BIG_RED',
        'signal_label': 'Big Red Dot — SELL',
        'direction':    'SELL',
        'wt1':          22.4321,
        'wt2':          25.1234,
        'timestamp':    now,
        'scan_time':    now_str,
    },
    {
        'symbol':       'BTCUSDT',
        'label':        'Bitcoin',
        'asset_type':   'crypto',
        'group':        'keep_an_eye',
        'timeframe':    '1w',
        'tf_label':     'Weekly',
        'signal_type':  'BIG_GREEN',
        'signal_label': 'Big Green Dot — BUY',
        'direction':    'BUY',
        'wt1':          -65.1234,
        'wt2':          -61.4321,
        'timestamp':    now,
        'scan_time':    now_str,
    },
    {
        'symbol':       'AVAXUSDT',
        'label':        'Avalanche',
        'asset_type':   'crypto',
        'group':        'keep_an_eye',
        'timeframe':    '1M',
        'tf_label':     'Monthly',
        'signal_type':  'YELLOW_BUY',
        'signal_label': 'Yellow — BUY',
        'direction':    'BUY',
        'wt1':          -15.2345,
        'wt2':          -12.1234,
        'timestamp':    now,
        'scan_time':    now_str,
    },
]

print()
print("VMC Cipher B Scanner — Sending 3 test alerts")
print("─" * 52)

for sig in test_signals:
    label  = f"{sig['signal_type']:13s} | {sig['symbol']:10s} | {sig['tf_label']}"
    result = manager.send_alert(sig)
    status = "✅ Sent" if result else "❌ Failed"
    print(f"  {status} → {label}")

print()
print("Check inbox for 3 emails:")
print("  🔴 URGENT — HOLDING | ALGOUSDT  | Weekly  | SELL")
print("  🟢 Keep an Eye      | BTCUSDT   | Weekly  | BUY")
print("  🟡 Keep an Eye      | AVAXUSDT  | Monthly | BUY")
print()
print("Confirm each email shows both UTC and PT times.")
print()