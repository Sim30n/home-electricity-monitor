#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PULSE_FQBN="Seeeduino:samd:seeed_XIAO_m0"
PULSE_PORT="/dev/ttyACM0"
PULSE_SKETCH="$SCRIPT_DIR/pulse_sensor/pulse_sensor"

ELE_FQBN="arduino:samd:mkrwifi1010"
ELE_IP="192.168.50.131"
ELE_OTA_PASSWORD="password"
ELE_SKETCH="$SCRIPT_DIR"

SERVICE_NAME="ele_monitor2"

green() { echo -e "\033[0;32m[✓]\033[0m $*"; }
info()  { echo -e "\033[0;34m[…]\033[0m $*"; }
err()   { echo -e "\033[0;31m[✗]\033[0m $*" >&2; exit 1; }

# ── 1. Pulse sensor (Seeeduino XIAO via USB) ─────────────────────────────────
info "Compiling pulse sensor..."
arduino-cli compile --fqbn "$PULSE_FQBN" "$PULSE_SKETCH" || err "Pulse sensor compile failed"
green "Pulse sensor compiled"

info "Uploading pulse sensor via USB ($PULSE_PORT)..."
arduino-cli upload -p "$PULSE_PORT" --fqbn "$PULSE_FQBN" "$PULSE_SKETCH" || err "Pulse sensor upload failed"
green "Pulse sensor uploaded"

# ── 2. ele_monitor2 (MKR WiFi 1010 via OTA) ──────────────────────────────────
info "Compiling ele_monitor2..."
arduino-cli compile --fqbn "$ELE_FQBN" "$ELE_SKETCH" || err "ele_monitor2 compile failed"
green "ele_monitor2 compiled"

info "Uploading ele_monitor2 via WiFi OTA ($ELE_IP)..."
if arduino-cli upload --help 2>&1 | grep -q -- "--upload-field"; then
  # arduino-cli >= 0.35: pass password directly
  arduino-cli upload -p "$ELE_IP" --fqbn "$ELE_FQBN" \
    --upload-field password="$ELE_OTA_PASSWORD" \
    "$ELE_SKETCH" || err "ele_monitor2 upload failed"
elif command -v expect &> /dev/null; then
  # Older arduino-cli: automate the interactive password prompt
  expect << EXPECT_SCRIPT || err "ele_monitor2 upload failed"
    set timeout 60
    spawn arduino-cli upload -p "$ELE_IP" --fqbn "$ELE_FQBN" "$ELE_SKETCH"
    expect -nocase "password"
    send "$ELE_OTA_PASSWORD\r"
    expect eof
EXPECT_SCRIPT
else
  err "arduino-cli < 0.35 and 'expect' is not installed. Either update arduino-cli (recommended) or: sudo apt install expect"
fi
green "ele_monitor2 uploaded"

# ── 3. Web app service ────────────────────────────────────────────────────────
info "Restarting $SERVICE_NAME service..."
sudo systemctl restart "$SERVICE_NAME" || err "Failed to restart $SERVICE_NAME"
green "$SERVICE_NAME restarted"

echo ""
green "Build complete!"
