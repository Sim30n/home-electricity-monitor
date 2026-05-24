# ele_monitor

Electricity consumption monitor. Reads pulses from an energy meter LED,
calculates power in real time, and displays current consumption and price
on an LCD.

## System overview

```
Energy meter LED
      ↓ light
  LDR on XIAO (A0)
      ↓ USB serial
  read_energy.py → energy_log.txt
      ↓
  ele_api.py (Flask)
      ↓ WiFi
  ele_monitor2 (MKR WiFi 1010) → LCD + LEDs
```

## First time setup

### 1. Configure secrets

Create `arduino_secrets.h` in the project root:

```cpp
#define SECRET_SSID   "wifi_name"
#define SECRET_PASS   "wifi_password"
#define SECRET_SERVER "server_ip"
#define SECRET_PORT   5000
```

See `arduino_secrets.example.h` for reference.

### 2. Install arduino-cli

```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
sudo mv ~/bin/arduino-cli /usr/local/bin/
arduino-cli core update-index
arduino-cli core install arduino:samd
```

See `pulse_sensor/README.md` for the Seeeduino XIAO core setup.

### 3. Set up the systemd services

**Web app:**
```bash
cd web_app
./create_service.sh
```

**Serial logger:**
```bash
cd pulse_sensor
./create_service.sh
```

Both services start on boot and restart automatically on failure.

## Build and deploy

Compile and deploy everything in one command:

```bash
./build.sh
```

Steps performed:
1. Compile and upload pulse sensor firmware to Seeeduino XIAO (USB)
2. Stop `read_energy` service to free the serial port
3. Upload firmware, then restart `read_energy`
4. Compile and upload ele_monitor2 to MKR WiFi 1010 (WiFi OTA)
5. Restart the `ele_monitor2` web app service

## Monitoring

```bash
# Serial logger output
journalctl -u read_energy -f

# Web app output
journalctl -u ele_monitor2 -f
```

## Manual build commands

### ele_monitor2 (MKR WiFi 1010)

```bash
arduino-cli compile --fqbn arduino:samd:mkrwifi1010 .
arduino-cli upload -p 192.168.50.131 --fqbn arduino:samd:mkrwifi1010 .
```

### Pulse sensor (Seeeduino XIAO)

See `pulse_sensor/README.md`.
