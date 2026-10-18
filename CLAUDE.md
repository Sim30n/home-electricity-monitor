# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

**ele_monitor** is a three-tier IoT electricity consumption monitor. It reads pulses from an energy meter's LED indicator, calculates real-time power consumption, correlates it with Finnish electricity spot prices from ENTSO-E, and displays the result on an LCD.

Data pipeline:

```
Energy meter LED
      ↓ light flashes (1000 pulses/kWh)
  LDR on Seeeduino XIAO (A0)
      ↓ USB serial (9600 baud)
  read_energy.py → energy_log.txt
      ↓
  ele_api.py (Flask, port 5000)
      ↓ WiFi HTTP polling (every 10s)
  ele_monitor2 (MKR WiFi 1010) → 16×2 LCD + status LEDs
```

## Build and deploy

**Deploy everything in one command:**
```bash
./build.sh
```

This compiles and uploads the pulse sensor firmware (XIAO via USB), stops/restarts the `read_energy` service around the upload, then compiles and uploads the display firmware (MKR WiFi 1010 via WiFi OTA), and restarts the Flask service.

**Manual builds:**
```bash
# MKR WiFi 1010 (display board)
arduino-cli compile --fqbn arduino:samd:mkrwifi1010 .
arduino-cli upload -p <device-ip> --fqbn arduino:samd:mkrwifi1010 .

# Seeeduino XIAO (pulse sensor)
arduino-cli compile --fqbn Seeeduino:samd:seeed_XIAO_m0 pulse_sensor/pulse_sensor
arduino-cli upload -p /dev/ttyACM0 --fqbn Seeeduino:samd:seeed_XIAO_m0 pulse_sensor/pulse_sensor
```

**Flask web app (development):**
```bash
cd web_app
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python ele_api.py
```

**Fetch spot prices manually:**
```bash
cd web_app
venv/bin/python ensto_e.py
```

## Monitoring running services

```bash
journalctl -u read_energy -f    # serial logger (pulse sensor → energy_log.txt)
journalctl -u ele_monitor2 -f   # Flask web app
```

## Architecture details

### Three firmware/software components

**`pulse_sensor/pulse_sensor/pulse_sensor.ino`** — runs on Seeeduino XIAO. Watches an LDR on pin A0 for LED flashes from the energy meter. Every 10 seconds it emits a CSV line over serial: `peakLDR;pulseCount;avgPowerKW;instantPowerKW`. Key thresholds: `thresholdHigh=500` (flash detected), `thresholdLow=200` (flash ended), `pulsesPerKWh=1000`.

**`pulse_sensor/read_energy.py`** — Python systemd service. Reads the XIAO serial output and appends timestamped lines to `pulse_sensor/energy_log.txt`. Format: `YYYY-MM-DD HH:MM:SS;peakLDR;pulses;avgPower;instantPower`.

**`ele_monitor2.ino`** — runs on MKR WiFi 1010. Polls `GET /api` over WiFi every 10 seconds and renders the response on a 16×2 LCD. LCD row 0: current price ("Hinta nyt: X.XX"). LCD row 1: 10-second average power and accumulated daily cost in euros ("kW:X.XX P:X.XXe"). Drives LEDs on GPIO 3/4/5 for price tier (green/yellow/red). Supports ArduinoOTA for wireless firmware updates.

### Flask API (`web_app/`)

`ele_api.py` serves `GET /api`. It reads price data from `price_info.py` (a Python dict literal, not JSON — loaded with `ast.literal_eval`), matches the current 15-minute window to find the active spot price, reads the most recent entry from `energy_log.txt` via `read_energy_log.py`, and calculates the accumulated electricity cost in euros since midnight from today's log entries and hourly prices. Response fields: `current_time`, `current_price`, `green_led`, `yellow_led`, `red_led`, `power`, `avg_power`, `daily_cost`.

`GET /` (alias `/dashboard`) renders `templates/dashboard.html`, a mobile friendly page with current usage and price plus daily energy and cost for the past 7 days; `GET /api/summary` returns the same data as JSON (built by `build_summary()` in `ele_api.py`). Weekly energy comes from pulse counts (`pulses / 1000` kWh per log line). Because `price_info.py` holds only one day, `price_store.py` keeps every price in `web_app/price_history.json` (gitignored) and backfills missing past days from ENTSO-E when a token is configured.

`price_info.py` is regenerated daily by a cron job running `ensto_e.py`, which fetches the next 24 hours of prices from the ENTSO-E Transparency Platform API. The file is a raw Python dict literal written to disk — this is intentional and replaces a database.

Price tiers (cents/kWh): green < 2, yellow 2–10, red ≥ 10.

### Secrets and configuration

- **Arduino**: `arduino_secrets.h` in project root (WiFi SSID, password, server IP:port). Not committed — use `arduino_secrets.example.h` as template.
- **Flask**: `web_app/.env` with `SECURITY_TOKEN` for ENTSO-E API. Not committed — use `web_app/.env.example` as template.
- **OTA password**: hardcoded as `"password"` in `build.sh` and `ele_monitor2.ino`.

### Systemd services

Both services are installed by their respective `create_service.sh` scripts:
- `read_energy` — serial logger, restarts every 5 seconds on failure
- `ele_monitor2` — Flask app, always restarts

The `read_energy` service must be stopped before uploading pulse sensor firmware (it holds the serial port). `build.sh` handles this automatically.

### File-based IPC

`energy_log.txt` is the coupling point between the sensor pipeline and the API. The serial logger appends to it continuously; the API reads only the last line on each request. This avoids shared-memory or socket complexity and allows the two processes to restart independently.

## First-time setup checklist

1. Create `arduino_secrets.h` from `arduino_secrets.example.h`
2. Install arduino-cli and cores: `arduino:samd` (MKR WiFi 1010) and `Seeeduino:samd` (XIAO — see `pulse_sensor/README.md`)
3. Set up Flask: `cd web_app && python3 -m venv venv && venv/bin/pip install -r requirements.txt && cp .env.example .env` (add ENTSO-E token)
4. Install systemd services: `cd web_app && ./create_service.sh` and `cd pulse_sensor && ./create_service.sh`
5. Add daily cron job: `0 0 * * * <path>/web_app/venv/bin/python <path>/web_app/ensto_e.py`
