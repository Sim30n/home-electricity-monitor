#!/bin/bash

SERVICE_NAME="read_energy"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME.service"
WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXE="/usr/bin/python3"
APP_PATH="$WORK_DIR/read_energy.py"

# Ensure pyserial is installed
if ! $PYTHON_EXE -c "import serial" 2>/dev/null; then
    echo "Installing pyserial..."
    pip3 install pyserial
fi

# Ensure pi user is in the dialout group for serial port access
if ! groups pi | grep -q dialout; then
    echo "Adding pi to dialout group..."
    sudo usermod -a -G dialout pi
    echo "Note: log out and back in (or reboot) for group change to take effect"
fi

echo "Creating systemd service file..."
cat <<EOF | sudo tee $SERVICE_PATH > /dev/null
[Unit]
Description=Read Energy Serial Logger
After=local-fs.target
# Restart handles reconnection if XIAO is not yet connected on boot

[Service]
User=pi
WorkingDirectory=$WORK_DIR
Environment=PYTHONUNBUFFERED=1
ExecStart=$PYTHON_EXE $APP_PATH
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

if systemctl is-active --quiet $SERVICE_NAME; then
    echo "Restarting existing service..."
    sudo systemctl restart $SERVICE_NAME
else
    echo "Starting new service..."
    sudo systemctl start $SERVICE_NAME
fi

sudo systemctl status $SERVICE_NAME --no-pager
