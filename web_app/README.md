# Web App

Flask API that combines real-time power consumption from the pulse sensor
with Finnish electricity spot prices from ENTSO-E, served to the LCD display
board over WiFi.

## Components

| File | Purpose |
|---|---|
| `ele_api.py` | Flask API endpoint (`GET /api`) |
| `ensto_e.py` | Fetches spot prices from ENTSO-E |
| `price_info.py` | Cached price data (updated daily by cron) |
| `price_store.py` | Keeps all fetched prices in `price_history.json` for the weekly view |
| `read_energy_log.py` | Parses `energy_log.txt` from the pulse sensor |
| `templates/dashboard.html` | Mobile friendly dashboard page |
| `create_service.sh` | Installs the Flask app as a systemd service |

## Setup

### 1. Create the virtual environment and install dependencies

```bash
cd web_app
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 2. Create the `.env` file

```bash
cp .env.example .env
```

Edit `.env` and add your ENTSO-E security token:

```
SECURITY_TOKEN=your_token_here
```

### 3. Install the systemd service

```bash
./create_service.sh
```

The service starts on boot and restarts automatically on failure.

Monitor logs:

```bash
journalctl -u ele_monitor2 -f
```

## API

**`GET /api`**

```json
{
  "current_time":  "2025-11-30T15:00:00+02:00",
  "current_price": 1.26,
  "green_led":     1,
  "yellow_led":    0,
  "red_led":       0,
  "power":         0.19,  // retained in API response but not shown on LCD
  "avg_power":     0.36,
  "daily_cost":    0.42
}
```

| Field | Description |
|---|---|
| `current_price` | Spot price in cents/kWh (markup + VAT included) |
| `green_led` | 1 when price < 2 c/kWh |
| `yellow_led` | 1 when 2 ≤ price < 10 c/kWh |
| `red_led` | 1 when price ≥ 10 c/kWh |
| `power` | Instantaneous power in kW (not shown on LCD) |
| `avg_power` | 10-second average power in kW |
| `daily_cost` | Accumulated electricity cost in euros since midnight today |

## Dashboard

**`GET /`** (also **`/dashboard`**) — mobile friendly page for a phone or
browser, e.g. `http://<server-ip>:5000/`. It shows:

- current spot price (with tier colour), average and instant power
- energy used and cost so far today
- current month's total energy, total cost, average cost per day and average
  price paid
- energy, cost and average price paid for each of the past 7 days, with totals

The page refreshes itself every 10 seconds. It uses no external libraries.

**`GET /api/summary`** — the same data as JSON.

Daily energy is the sum of the logged pulse counts (1000 pulses = 1 kWh), and
each log line is priced with the spot price (plus markup and VAT) of the
15-minute or hourly slot it falls in. Results for finished days are kept in
memory, so a month of log data is read only once per service start.

`price_info.py` only holds the latest day, so every price seen is also kept in
`price_history.json` (not committed). Past days without stored prices are
fetched from ENTSO-E once per service start when `SECURITY_TOKEN` is set;
consumption without a price is shown separately and left out of the costs.

## Price data — daily cron job

`ensto_e.py` fetches the next 24 hours of spot prices and writes them to
`price_info.py`. Set it up to run daily at midnight:

```bash
crontab -e
```

Add:

```
0 0 * * * <path_to_project>/web_app/venv/bin/python <path_to_project>/web_app/ensto_e.py
```

Verify the cron job is registered:

```bash
crontab -l
```

Run manually to test:

```bash
venv/bin/python ensto_e.py
```

## Troubleshooting

**Service not starting**
```bash
journalctl -u ele_monitor2 -n 50
```

**Price data stale or missing**
```bash
# Check cron logs
grep CRON /var/log/syslog

# Run price fetch manually
venv/bin/python ensto_e.py
```

**API returns wrong power values**
- Check `../pulse_sensor/energy_log.txt` has recent entries
- Check the `read_energy` service: `journalctl -u read_energy -f`
