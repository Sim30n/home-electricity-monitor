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