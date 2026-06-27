import os
import sys
import threading
import tempfile
import time
from datetime import datetime

from robot.api.deco import keyword

_WEB_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WEB_APP_DIR not in sys.path:
    sys.path.insert(0, _WEB_APP_DIR)

from werkzeug.serving import make_server
from read_energy_log import EnergyLogReader
from ensto_e import ElePrice
import ele_api
import pytz

_PRICE_INFO_PATH = os.path.join(_WEB_APP_DIR, 'price_info.py')
_FLASK_PORT = 5099


class EleKeywords:

    def __init__(self):
        self._server = None
        self._thread = None
        self._temp_files = []
        self._original_price_info = None
        self._default_log_path = None

    # ------------------------------------------------------------------
    # Flask lifecycle
    # ------------------------------------------------------------------

    @keyword
    def setup_api_tests(self):
        """Create a test log with today's data, write a default price, start Flask."""
        log_path = self.create_single_entry_log(1.2, 1.5)
        self._default_log_path = log_path

        if os.path.exists(_PRICE_INFO_PATH):
            with open(_PRICE_INFO_PATH, 'r') as f:
                self._original_price_info = f.read()

        self._write_price_file(1.0)
        ele_api.energy_log_reader = EnergyLogReader(log_path)

        self._server = make_server('127.0.0.1', _FLASK_PORT, ele_api.app)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        time.sleep(0.3)

    @keyword
    def teardown_api_tests(self):
        """Stop Flask and restore price_info.py."""
        if self._server:
            self._server.shutdown()
            self._server = None
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        if self._original_price_info is not None:
            with open(_PRICE_INFO_PATH, 'w') as f:
                f.write(self._original_price_info)
            self._original_price_info = None
        self.cleanup_temp_files()

    @keyword
    def set_test_price(self, spot_price_cents):
        """Write price_info.py with the current hour slot and given spot price."""
        self._write_price_file(float(spot_price_cents))

    @keyword
    def set_log_file(self, filepath):
        """Redirect ele_api's energy log reader to the given file."""
        ele_api.energy_log_reader = EnergyLogReader(filepath)

    @keyword
    def restore_default_log(self):
        """Restore ele_api's energy log reader to the default test log."""
        if self._default_log_path:
            ele_api.energy_log_reader = EnergyLogReader(self._default_log_path)

    # ------------------------------------------------------------------
    # Log file factories
    # ------------------------------------------------------------------

    @keyword
    def create_header_only_log(self):
        """Return path to a log file containing only the header line."""
        return self._write_temp("datetime;LDR;Pulses/min;Power(kW)\n")

    @keyword
    def create_single_entry_log(self, power_kw, instant_kw=0.0):
        """Return path to a log with header + one data row for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        content = (
            "datetime;LDR;Pulses/min;Power(kW);instantPower(kW)\n"
            f"{today} 10:00:00;450;17;{float(power_kw):.3f};{float(instant_kw):.3f}\n"
        )
        return self._write_temp(content)

    @keyword
    def create_multi_entry_log(self, *power_values):
        """Return path to a log with header + one row per power value (all today)."""
        today = datetime.now().strftime("%Y-%m-%d")
        lines = ["datetime;LDR;Pulses/min;Power(kW)"]
        for i, p in enumerate(power_values):
            lines.append(f"{today} 10:00:{i:02d};450;17;{float(p):.3f}")
        return self._write_temp('\n'.join(lines) + '\n')

    @keyword
    def create_mixed_date_log(self, *power_values):
        """Return path to a log with today's rows plus one row from 2020-01-01."""
        today = datetime.now().strftime("%Y-%m-%d")
        lines = ["datetime;LDR;Pulses/min;Power(kW)"]
        for i, p in enumerate(power_values):
            lines.append(f"{today} 10:00:{i:02d};450;17;{float(p):.3f}")
        lines.append("2020-01-01 10:00:00;400;10;0.800")
        return self._write_temp('\n'.join(lines) + '\n')

    @keyword
    def create_malformed_log(self, power_kw_first, power_kw_second):
        """Return path to a log with one valid entry, one malformed, one valid."""
        today = datetime.now().strftime("%Y-%m-%d")
        lines = [
            "datetime;LDR;Pulses/min;Power(kW)",
            f"{today} 10:00:00;450;17;{float(power_kw_first):.3f}",
            f"{today} MALFORMED",
            f"{today} 10:00:20;460;16;{float(power_kw_second):.3f}",
        ]
        return self._write_temp('\n'.join(lines) + '\n')

    # ------------------------------------------------------------------
    # Temp file management
    # ------------------------------------------------------------------

    @keyword
    def create_temp_log_file(self, content):
        """Write content to a new temp file and return its path."""
        return self._write_temp(content)

    @keyword
    def cleanup_temp_files(self):
        """Delete all temp files created in this session."""
        for path in self._temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        self._temp_files.clear()

    # ------------------------------------------------------------------
    # Readers
    # ------------------------------------------------------------------

    @keyword
    def read_latest_log_data(self, filepath):
        """Return (datetime_str, avg_kw, instant_kw) tuple or None."""
        return EnergyLogReader(filepath).get_latest_data()

    @keyword
    def read_today_log_data(self, filepath):
        """Return list of today's log entries."""
        return EnergyLogReader(filepath).get_today_data()

    @keyword
    def read_all_log_data(self, filepath):
        """Return list of all log entries."""
        return EnergyLogReader(filepath).get_all_data()

    # ------------------------------------------------------------------
    # Price XML
    # ------------------------------------------------------------------

    @keyword
    def parse_price_xml(self, xml_text):
        """Parse ENTSO-E XML and return price dict."""
        class _Resp:
            def __init__(self, t):
                self.text = t
        return ElePrice().format_price_to_dict(_Resp(xml_text))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @keyword
    def calculate_expected_price(self, spot_price_cents):
        """Return (spot + 0.59) * 1.24 rounded to 4 decimal places."""
        return round((float(spot_price_cents) + 0.59) * 1.24, 4)

    def _write_temp(self, content):
        fd, path = tempfile.mkstemp(suffix='.log')
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        self._temp_files.append(path)
        return path

    def _write_price_file(self, spot_price_cents):
        tz = pytz.timezone('Europe/Helsinki')
        now = datetime.now(tz)
        slot = now.replace(minute=0, second=0, microsecond=0)
        price_dict = {slot.isoformat(): spot_price_cents}
        with open(_PRICE_INFO_PATH, 'w') as f:
            f.write(str(price_dict))
