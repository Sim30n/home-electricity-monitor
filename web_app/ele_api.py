from flask import Flask, jsonify, render_template
from ensto_e import ElePrice
from read_energy_log import EnergyLogReader
from price_store import get_price_lookup
from datetime import datetime, timedelta
import ast
import os

example_response = {
    "2025-01-25T01:00:00+02:00": 0.279,
    "2025-01-25T02:00:00+02:00": 0.23199999999999998,
    "2025-01-25T03:00:00+02:00": 0.126,
    "2025-01-25T04:00:00+02:00": 0.101,
    "2025-01-25T05:00:00+02:00": 0.097,
    "2025-01-25T06:00:00+02:00": 0.074,
    "2025-01-25T07:00:00+02:00": 0.125,
    "2025-01-25T08:00:00+02:00": 0.22200000000000003,
    "2025-01-25T09:00:00+02:00": 0.279,
    "2025-01-25T10:00:00+02:00": 0.307,
    "2025-01-25T11:00:00+02:00": 0.291,
    "2025-01-25T12:00:00+02:00": 0.275,
    "2025-01-25T13:00:00+02:00": 0.295,
    "2025-01-25T14:00:00+02:00": 0.261,
    "2025-01-25T15:00:00+02:00": 0.25099999999999995,
    "2025-01-25T16:00:00+02:00": 0.216,
    "2025-01-25T17:00:00+02:00": 0.229,
    "2025-01-25T18:00:00+02:00": 0.2,
    "2025-01-25T19:00:00+02:00": 0.227,
    "2025-01-25T20:00:00+02:00": 0.194,
    "2025-01-25T21:00:00+02:00": 0.199,
    "2025-01-25T22:00:00+02:00": 0.176,
    "2025-01-25T23:00:00+02:00": 0.14,
    "2025-01-26T00:00:00+02:00": 0.026,
    "2025-01-26T01:00:00+02:00": 0.126,
    "2025-01-26T02:00:00+02:00": 0.121,
    "2025-01-26T03:00:00+02:00": 0.137,
    "2025-01-26T04:00:00+02:00": 0.145,
    "2025-01-26T05:00:00+02:00": 0.20099999999999998,
    "2025-01-26T06:00:00+02:00": 0.227,
    "2025-01-26T07:00:00+02:00": 0.216,
    "2025-01-26T08:00:00+02:00": 0.237,
    "2025-01-26T09:00:00+02:00": 0.238,
    "2025-01-26T10:00:00+02:00": 0.223,
    "2025-01-26T11:00:00+02:00": 0.279,
    "2025-01-26T12:00:00+02:00": 0.324,
    "2025-01-26T13:00:00+02:00": 0.4059999999999999,
    "2025-01-26T14:00:00+02:00": 0.463,
    "2025-01-26T15:00:00+02:00": 0.508,
    "2025-01-26T16:00:00+02:00": 1.716,
    "2025-01-26T17:00:00+02:00": 2.468,
    "2025-01-26T18:00:00+02:00": 3.7020000000000004,
    "2025-01-26T19:00:00+02:00": 4.434,
    "2025-01-26T20:00:00+02:00": 4.433,
    "2025-01-26T21:00:00+02:00": 3.8979999999999997,
    "2025-01-26T22:00:00+02:00": 4.542,
    "2025-01-26T23:00:00+02:00": 3.56,
    "2025-01-27T00:00:00+02:00": 2.692
}

example2 = {
    "current_time": "2025-01-27T00:00:00+02:00",
    "current_price": 2.54,
    "green_led": 1,
    "yellow_led": 1,
    "red_led": 0
}

# Price adjustment: markup (c/kWh) added to spot price, then VAT multiplied on top
PRICE_MARKUP_CENTS = 0.59
PRICE_TAX_RATE = 0.24  # 24 % VAT

energy_log_reader = EnergyLogReader()


def calculate_daily_cost(price_dict):
    """Return accumulated electricity cost in euros since midnight today."""
    today_entries = energy_log_reader.get_today_data()
    if not today_entries:
        return 0.0

    total_cost_cents = 0.0
    interval_hours = 10.0 / 3600.0

    for entry in today_entries:
        entry_dt = datetime.strptime(entry['datetime'], "%Y-%m-%d %H:%M:%S")
        for price_key, price_val in price_dict.items():
            slot_dt = datetime.fromisoformat(price_key)
            if (entry_dt.year == slot_dt.year and
                    entry_dt.month == slot_dt.month and
                    entry_dt.day == slot_dt.day and
                    entry_dt.hour == slot_dt.hour):
                price_with_markup = (price_val + PRICE_MARKUP_CENTS) * (1 + PRICE_TAX_RATE)
                total_cost_cents += entry['power_kw'] * interval_hours * price_with_markup
                break

    return round(total_cost_cents / 100.0, 2)

PULSES_PER_KWH = 1000
SUMMARY_DAYS = 7

# Stats of finished days, so their log lines are not re-read on every request
_day_stats_cache = {}


def price_with_markup(spot_price):
    """Spot price (c/kWh) -> consumer price with markup and VAT (c/kWh)."""
    return (spot_price + PRICE_MARKUP_CENTS) * (1 + PRICE_TAX_RATE)


def price_tier(price):
    if price is None:
        return None
    if price < 2:
        return "green"
    if price < 10:
        return "yellow"
    return "red"


def collect_day_stats(days, lookup, today):
    """Return {date: stats} with energy, cost and peak power for each day.

    Energy comes from the pulse count of each log line (1000 pulses = 1 kWh)
    and each line is priced with the spot price of the slot it was logged in.
    Days before today are cached once computed.
    """
    stats = {day: _day_stats_cache[day] for day in days if day in _day_stats_cache}
    pending = [day for day in days if day not in stats]
    if not pending:
        return stats

    for day in pending:
        stats[day] = {"energy_kwh": 0.0, "cost_cents": 0.0, "unpriced_kwh": 0.0,
                      "peak_kw": 0.0, "entries": 0, "latest": None}
    pending_set = set(pending)
    entries = energy_log_reader.get_data_since(datetime.combine(pending[0], datetime.min.time()))
    for entry in entries:
        day = entry['datetime'].date()
        if day not in pending_set:
            continue
        day_stats = stats[day]
        kwh = entry['pulses'] / PULSES_PER_KWH
        day_stats["energy_kwh"] += kwh
        day_stats["entries"] += 1
        day_stats["peak_kw"] = max(day_stats["peak_kw"], entry['power_kw'])
        day_stats["latest"] = entry
        spot = lookup(entry['datetime'])
        if spot is None:
            day_stats["unpriced_kwh"] += kwh
        else:
            day_stats["cost_cents"] += kwh * price_with_markup(spot)

    # An empty read may be a log read error, so only cache when lines were found
    for day in pending:
        if day < today and entries:
            _day_stats_cache[day] = stats[day]
    return stats


def summarize_period(day_stats):
    """Totals and daily averages over a list of day stats."""
    total_kwh = sum(d["energy_kwh"] for d in day_stats)
    total_cents = sum(d["cost_cents"] for d in day_stats)
    total_unpriced = sum(d["unpriced_kwh"] for d in day_stats)
    priced_kwh = total_kwh - total_unpriced
    days_with_data = sum(1 for d in day_stats if d["entries"] > 0)
    days_priced = sum(1 for d in day_stats if d["energy_kwh"] > d["unpriced_kwh"])
    return {
        "energy_kwh": round(total_kwh, 3),
        "cost_eur": round(total_cents / 100.0, 2),
        "avg_price": round(total_cents / priced_kwh, 2) if priced_kwh > 0 else None,
        "unpriced_kwh": round(total_unpriced, 3),
        "days_with_data": days_with_data,
        "avg_daily_kwh": round(total_kwh / days_with_data, 3) if days_with_data else None,
        "avg_daily_cost_eur": round(total_cents / 100.0 / days_priced, 2) if days_priced else None,
    }


def build_summary(now=None):
    """Current usage and price, daily energy and cost for the past week,
    and totals for the current month."""
    now = now or datetime.now()
    today = now.date()
    week_start = today - timedelta(days=SUMMARY_DAYS - 1)
    month_start = today.replace(day=1)
    first_day = min(week_start, month_start)
    days = [first_day + timedelta(days=i) for i in range((today - first_day).days + 1)]
    lookup = get_price_lookup(days)
    stats = collect_day_stats(days, lookup, today)

    week_days = [day for day in days if day >= week_start]
    daily = []
    for day in week_days:
        d = stats[day]
        priced_kwh = d["energy_kwh"] - d["unpriced_kwh"]
        daily.append({
            "date": day.isoformat(),
            "energy_kwh": round(d["energy_kwh"], 3),
            "cost_eur": round(d["cost_cents"] / 100.0, 2),
            "avg_price": round(d["cost_cents"] / priced_kwh, 2) if priced_kwh > 0 else None,
            "unpriced_kwh": round(d["unpriced_kwh"], 3),
            "peak_kw": round(d["peak_kw"], 2),
            "has_data": d["entries"] > 0,
        })

    month = summarize_period([stats[day] for day in days if day >= month_start])
    month["month"] = month_start.strftime("%Y-%m")

    spot_now = lookup(now)
    current_price = round(price_with_markup(spot_now), 2) if spot_now is not None else None
    latest = next((stats[day]["latest"] for day in reversed(week_days) if stats[day]["latest"]), None)

    return {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "current": {
            "price": current_price,
            "tier": price_tier(current_price),
            "avg_power": round(latest['power_kw'], 2) if latest else None,
            "power": round(latest['instant_power_kw'], 2)
                     if latest and latest['instant_power_kw'] is not None else None,
            "measured_at": latest['datetime'].strftime("%Y-%m-%d %H:%M:%S") if latest else None,
        },
        "today": daily[-1],
        "daily": daily,
        "week": summarize_period([stats[day] for day in week_days]),
        "month": month,
    }


# Initialize the Flask application
app = Flask(__name__)

# Define a single endpoint
@app.route('/api', methods=['GET'])
def api_endpoint():
    """A simple API endpoint that returns a JSON response."""
    # Construct the file path
    file_path = os.path.join(os.path.dirname(__file__), "price_info.py")

    with open(file_path, 'r') as file:
        file_content = file.read()

    # Convert the string content to a dictionary
    price_dict = ast.literal_eval(file_content)
    for key, value in price_dict.items():
        # Target ISO 8601 datetime string
        target_datetime_str = key

        # Parse the target datetime
        target_datetime = datetime.fromisoformat(target_datetime_str)

        # Get the current datetime in the same timezone
        current_datetime = datetime.now(target_datetime.tzinfo)

        # Check if the current datetime is in the same 15min as the target datetime
        is_same_hour = (
            current_datetime.year == target_datetime.year and
            current_datetime.month == target_datetime.month and
            current_datetime.day == target_datetime.day and
            current_datetime.hour == target_datetime.hour and
            (current_datetime.minute // 15) == (target_datetime.minute // 15)
        )
        price_to_send = 999
        if is_same_hour:
            price_to_send = (value + PRICE_MARKUP_CENTS) * (1 + PRICE_TAX_RATE)
            break
            #print(key, value)

    if price_to_send < 2:
        g_led = 1
        y_led = 0
        r_led = 0
    elif 2 <= price_to_send < 10:
        g_led = 0
        y_led = 1
        r_led = 0
    else:  # price_to_send >= 10
        g_led = 0
        y_led = 0
        r_led = 1
    
    latest_power_data = energy_log_reader.get_latest_data()

    response = {
        "current_time": target_datetime_str,
        "current_price": price_to_send,
        "green_led": g_led,
        "yellow_led": y_led,
        "red_led": r_led,
        "power": round(latest_power_data[2], 2),
        "avg_power": round(latest_power_data[1], 2),
        "daily_cost": calculate_daily_cost(price_dict),
    }

    #ele_price = ElePrice()
    #price_data = ele_price.get_price_info()
    #json_format = ele_price.format_price_to_dict(price_data)

    #print(json_format)
    #response = {
    #    "message": "Hello, World!",
    #    "status": "success",
    #    "data": None
    #}
    return jsonify(response)


@app.route('/api/summary', methods=['GET'])
def summary_endpoint():
    """Current usage and price plus a daily breakdown of the past week."""
    return jsonify(build_summary())


@app.route('/', methods=['GET'])
@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Mobile friendly page showing the data from /api/summary."""
    return render_template('dashboard.html', summary=build_summary())


# Run the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
