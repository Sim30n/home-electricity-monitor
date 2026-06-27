#!/bin/bash

SERVICE_NAME="ele_monitor2"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME.service"
WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXE="$WORK_DIR/venv/bin/python3"
APP_PATH="$WORK_DIR/ele_api.py"

# Create the service file
echo "Creating systemd service file..."
cat <<EOF | sudo tee $SERVICE_PATH > /dev/null
[Unit]
Description=Ele Monitor 2 Web App Service
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$WORK_DIR
ExecStart=$PYTHON_EXE $APP_PATH
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable $SERVICE_NAME

# Check if the service is already running
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "Restarting existing service..."
    sudo systemctl restart $SERVICE_NAME
else
    echo "Starting new service..."
    sudo systemctl start $SERVICE_NAME
fi

# Show service status
sudo systemctl status $SERVICE_NAME --no-pager
