"""Persistent spot price history.

price_info.py only holds the latest day's prices (it is overwritten by the
daily cron job), so this module keeps every price seen in price_history.json.
Missing past days can be backfilled from ENTSO-E when a SECURITY_TOKEN is set.
"""
from bisect import bisect_right
from datetime import datetime, timedelta
import ast
import json
import os

import pytz

from ensto_e import ElePrice

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRICE_INFO_PATH = os.path.join(BASE_DIR, "price_info.py")
PRICE_HISTORY_PATH = os.path.join(BASE_DIR, "price_history.json")
FINNISH_TZ = pytz.timezone("Europe/Helsinki")

# Days already requested from ENTSO-E by this process, so a failing
# backfill is not retried on every page refresh
_backfill_attempted = set()


def load_price_info():
    """Return the price_info.py dict (ISO timestamp -> c/kWh)."""
    try:
        with open(PRICE_INFO_PATH, 'r') as file:
            return ast.literal_eval(file.read())
    except (OSError, ValueError, SyntaxError) as e:
        print(f"Error reading price info: {e}")
        return {}


def load_history():
    try:
        with open(PRICE_HISTORY_PATH, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:
        print(f"Error reading price history: {e}")
        return {}


def save_history(history):
    tmp_path = PRICE_HISTORY_PATH + ".tmp"
    with open(tmp_path, 'w') as file:
        json.dump(history, file, sort_keys=True)
    os.replace(tmp_path, PRICE_HISTORY_PATH)


def merge_into_history(prices):
    """Add prices (ISO timestamp -> c/kWh) to the history file."""
    history = load_history()
    if all(history.get(k) == v for k, v in prices.items()):
        return history
    history.update(prices)
    save_history(history)
    return history


def _days_with_prices(history):
    return {to_local_naive(key).date() for key in history}


def to_local_naive(iso_key):
    """Convert an ISO timestamp key to naive Finnish local time (as in energy_log.txt)."""
    return datetime.fromisoformat(iso_key).astimezone(FINNISH_TZ).replace(tzinfo=None)


def backfill_missing_days(history, days):
    """Fetch prices from ENTSO-E for the given dates that have no prices yet."""
    if not os.getenv('SECURITY_TOKEN'):
        return history
    known = _days_with_prices(history)
    missing = sorted(d for d in days if d not in known and d not in _backfill_attempted)
    if not missing:
        return history

    ele_price = ElePrice()
    prices = {}
    # One request per day: format_price_to_dict reads a single period per series
    for day in missing:
        _backfill_attempted.add(day)
        midnight = datetime.combine(day, datetime.min.time())
        # The API takes UTC times; start early so the local morning hours are included
        try:
            response = ele_price.get_price_info(midnight - timedelta(hours=3), midnight + timedelta(days=1))
            prices.update(ele_price.format_price_to_dict(response))
        except Exception as e:
            print(f"Error backfilling prices for {day}: {e}")
    return merge_into_history(prices) if prices else history


def get_price_lookup(days=()):
    """Return a lookup function: naive local datetime -> spot price (c/kWh) or None.

    Works with both 15-minute and hourly price resolution. days lists the
    dates the caller needs; any of them without prices are backfilled.
    """
    history = merge_into_history(load_price_info())
    history = backfill_missing_days(history, days)

    slots = sorted((to_local_naive(key), value) for key, value in history.items())
    slot_times = [t for t, _ in slots]

    def lookup(dt):
        # The price slot is the latest one starting at or before dt. ENTSO-E
        # omits repeated points, so a slot may last longer than its resolution;
        # anything over an hour old means the price is genuinely missing.
        i = bisect_right(slot_times, dt) - 1
        if i < 0 or dt - slot_times[i] >= timedelta(hours=1):
            return None
        return slots[i][1]

    return lookup
