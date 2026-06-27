#!/usr/bin/env bash
# install.sh
# ─────────────────────────────────────────────────────────────────────────────
# One-command setup script for Ubuntu 22.04 VPS (or any Linux system).
# Run: chmod +x install.sh && ./install.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e  # Exit immediately on any error

echo ""
echo "=================================================="
echo "  VMC Cipher B Scanner — Installation Script"
echo "=================================================="
echo ""

# ── System dependencies ────────────────────────────────────────────────────
echo "[1/6] Updating system packages..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv screen -qq

echo "[2/6] Python version:"
python3 --version

# ── Project directory ──────────────────────────────────────────────────────
PROJECT_DIR="$HOME/vmc-scanner"

echo "[3/6] Setting up project directory at $PROJECT_DIR..."
mkdir -p "$PROJECT_DIR/data"
mkdir -p "$PROJECT_DIR/logs"

cd "$PROJECT_DIR"

# ── Virtual environment ────────────────────────────────────────────────────
echo "[4/6] Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# ── Python packages ────────────────────────────────────────────────────────
echo "[5/6] Installing Python packages..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "[6/6] Installation complete."
echo ""
echo "=================================================="
echo "  Next steps:"
echo ""
echo "  1. Edit config.py:"
echo "     GMAIL_SENDER   = 'your_gmail@gmail.com'"
echo "     GMAIL_APP_PASS = 'xxxx xxxx xxxx xxxx'"
echo ""
echo "  2. Test Gmail:"
echo "     source venv/bin/activate"
echo "     python test_gmail.py"
echo ""
echo "  3. Validate signals:"
echo "     python test_signals.py --symbol BTCUSDT --tf 1d"
echo ""
echo "  4. Start the scanner:"
echo "     screen -S vmc-scanner"
echo "     python main.py"
echo "     (Detach: Ctrl+A then D)"
echo ""
echo "  5. For auto-restart on VPS reboot, run:"
echo "     sudo bash setup_service.sh"
echo "=================================================="
echo ""