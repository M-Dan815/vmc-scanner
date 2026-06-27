#!/usr/bin/env bash
# setup_service.sh
# Installs scanner as systemd service with correct root path.

set -e

CURRENT_USER=$(logname 2>/dev/null || echo "$SUDO_USER" || echo "root")

# Fix for root user — home is /root not /home/root
if [ "$CURRENT_USER" = "root" ]; then
  PROJECT_DIR="/root/vmc-scanner"
else
  PROJECT_DIR="/home/$CURRENT_USER/vmc-scanner"
fi

VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
SERVICE_FILE="/etc/systemd/system/vmc-scanner.service"

echo ""
echo "Installing VMC Cipher B Scanner as systemd service..."
echo "User: $CURRENT_USER"
echo "Path: $PROJECT_DIR"
echo ""

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=VMC Cipher B Alert Scanner
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$VENV_PYTHON $PROJECT_DIR/main.py
Restart=always
RestartSec=15
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable vmc-scanner
systemctl start  vmc-scanner

echo ""
echo "=================================================="
echo "  Service installed and started."
echo ""
echo "  Useful commands:"
echo "  sudo systemctl status  vmc-scanner   # Check status"
echo "  sudo systemctl stop    vmc-scanner   # Stop scanner"
echo "  sudo systemctl restart vmc-scanner   # Restart scanner"
echo "  sudo journalctl -u vmc-scanner -f    # Live logs"
echo "=================================================="
echo ""