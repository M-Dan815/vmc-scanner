# VMC Cipher B Alert Scanner

Automated multi-timeframe crypto signal alerts via Gmail.
Replicates the VMC Cipher B + Divergences WaveTrend logic
from the open-source Pine Script — no TradingView needed.

## What It Does

- Monitors 20 crypto assets across 4-Hour, Daily, Weekly, and Monthly timeframes
- Detects Big Green Dot (Buy) and Big Red Dot (Sell) signals
- Sends formatted Gmail alerts the moment a signal appears on a confirmed candle
- Runs 24/7 on a VPS with no TradingView subscription required

## Quick Start (VPS)

```bash
# 1. Upload files to VPS then run:
chmod +x install.sh && ./install.sh

# 2. Configure Gmail in config.py
#    GMAIL_SENDER   = "your_gmail@gmail.com"
#    GMAIL_APP_PASS = "xxxx xxxx xxxx xxxx"

# 3. Test Gmail
source venv/bin/activate
python test_gmail.py

# 4. Validate signals against TradingView
python test_signals.py --symbol BTCUSDT --tf 1d
python test_signals.py --all

# 5. Start scanner
screen -S vmc-scanner
python main.py

# 6. Install as system service (auto-restart on reboot)
sudo bash setup_service.sh
```
