from datetime import datetime

class EnergyLogReader:
    """Class for reading and parsing energy log data."""
    
    def __init__(self, filepath=None):
        """
        Initialize with optional custom filepath.
        Defaults to pulse_sensor\energy_log.txt in the project directory.
        """
        if filepath is None:
            filepath = r"../pulse_sensor/energy_log.txt"
        self.filepath = filepath
    
    def get_latest_data(self):
        """Reads the last line and returns (datetime, avg_kw, instant_kw)."""
        try:
            with open(self.filepath, 'r') as file:
                lines = file.readlines()
                if len(lines) > 1:  # Skip header line
                    last_line = lines[-1].strip()
                    columns = last_line.split(';')
                    datetime_str = columns[0]
                    avg_kw = float(columns[3])
                    instant_kw = float(columns[4]) if len(columns) > 4 else 0.0
                    return datetime_str, avg_kw, instant_kw
                else:
                    return None
        except (FileNotFoundError, IndexError, ValueError) as e:
            print(f"Error reading data: {e}")
            return None
    
    def get_today_data(self):
        """Returns today's log entries (since midnight) by reading from end of file."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        entries = []
        try:
            with open(self.filepath, 'rb') as f:
                f.seek(0, 2)
                file_size = f.tell()
                read_size = min(500 * 1024, file_size)
                f.seek(-read_size, 2)
                chunk = f.read().decode('utf-8', errors='replace')
                for line in chunk.split('\n'):
                    stripped = line.strip()
                    if stripped.startswith(today_str):
                        parts = stripped.split(';')
                        if len(parts) >= 4:
                            try:
                                entries.append({'datetime': parts[0], 'power_kw': float(parts[3])})
                            except (ValueError, IndexError):
                                pass
        except Exception as e:
            print(f"Error reading today's data: {e}")
        return entries

    def get_data_since(self, since_dt, block_size=64 * 1024):
        """Returns entries logged at or after since_dt, oldest first.

        Reads the file backwards in blocks so only the tail needed for the
        requested period is parsed. Each entry has 'datetime' (datetime),
        'pulses' (int, pulses in that log interval), 'power_kw' (float) and
        'instant_power_kw' (float, or None for old log lines).
        """
        entries = []
        try:
            with open(self.filepath, 'rb') as f:
                f.seek(0, 2)
                position = f.tell()
                remainder = b''
                done = False
                while position > 0 and not done:
                    read_size = min(block_size, position)
                    position -= read_size
                    f.seek(position)
                    lines = (f.read(read_size) + remainder).split(b'\n')
                    # The first line may be cut in the middle; keep it for the next block
                    remainder = lines.pop(0) if position > 0 else b''
                    for raw in reversed(lines):
                        entry = self._parse_line(raw)
                        if entry is None:
                            continue
                        if entry['datetime'] < since_dt:
                            done = True
                            break
                        entries.append(entry)
        except Exception as e:
            print(f"Error reading log data: {e}")
        entries.reverse()
        return entries

    @staticmethod
    def _parse_line(raw):
        parts = raw.decode('utf-8', errors='replace').strip().split(';')
        if len(parts) < 4:
            return None
        try:
            return {
                'datetime': datetime.fromisoformat(parts[0]),
                'pulses': int(parts[2]),
                'power_kw': float(parts[3]),
                'instant_power_kw': float(parts[4]) if len(parts) > 4 else None,
            }
        except ValueError:
            return None  # header or corrupted line

    def get_all_data(self):
        """Returns list of dictionaries with all log entries."""
        try:
            with open(self.filepath, 'r') as file:
                lines = file.readlines()
                if len(lines) <= 1:
                    return []

                data = []
                for line in lines[1:]:  # Skip header
                    parts = line.strip().split(';')
                    entry = {
                        'datetime': parts[0],
                        'ldr': int(parts[1]),
                        'pulses_per_min': int(parts[2]),
                        'power_kw': float(parts[3]),
                    }
                    if len(parts) > 4:
                        entry['instant_power_kw'] = float(parts[4])
                    data.append(entry)
                return data
        except Exception as e:
            print(f"Error reading log file: {e}")
            return []

if __name__ == "__main__":
    reader = EnergyLogReader()
    latest_data = reader.get_latest_data()
    if latest_data:
        print(f"Latest Data - Datetime: {latest_data[0]}, Avg (kW): {latest_data[1]}, Instant (kW): {latest_data[2]}")
    else:
        print("No data available.")