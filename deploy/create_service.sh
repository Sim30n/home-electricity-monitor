#!/bin/bash

SERVICE_NAME="ele_deploy"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME.service"
TIMER_PATH="/etc/systemd/system/$SERVICE_NAME.timer"
WORK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$WORK_DIR/.." && pwd)"
RUN_USER=$(whoami)
SYSTEMCTL=$(command -v systemctl)

# build.sh runs sudo systemctl with no terminal to type a password into, so
# allow exactly the commands it needs — nothing more.
echo "Creating scoped sudoers rule..."
cat <<EOF | sudo tee /etc/sudoers.d/$SERVICE_NAME > /dev/null
$RUN_USER ALL=(root) NOPASSWD: $SYSTEMCTL stop read_energy, $SYSTEMCTL start read_energy, $SYSTEMCTL restart read_energy, $SYSTEMCTL restart ele_monitor2
EOF
sudo chmod 440 /etc/sudoers.d/$SERVICE_NAME

# Seed the deploy state with the current commit so installing the timer
# doesn't immediately reflash boards that are already up to date.
if [ ! -f "$REPO_DIR/.last_deploy" ]; then
    git -C "$REPO_DIR" rev-parse HEAD > "$REPO_DIR/.last_deploy"
fi

echo "Creating systemd service file..."
cat <<EOF | sudo tee $SERVICE_PATH > /dev/null
[Unit]
Description=Ele Monitor pull-based deploy (fetch master, run build.sh)
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User=$RUN_USER
WorkingDirectory=$REPO_DIR
ExecStart=/bin/bash $WORK_DIR/auto_deploy.sh
TimeoutStartSec=30min
EOF

echo "Creating systemd timer file..."
cat <<EOF | sudo tee $TIMER_PATH > /dev/null
[Unit]
Description=Poll origin/master every 2 minutes and deploy new commits

[Timer]
OnBootSec=2min
OnUnitInactiveSec=2min

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now $SERVICE_NAME.timer

sudo systemctl status $SERVICE_NAME.timer --no-pager
