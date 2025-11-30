import serial
import time
from datetime import datetime

# --- CONFIGURE YOUR SERIAL PORT HERE ---
SERIAL_PORT = "/dev/ttyACM0"      # Windows example: "COM3"
# Linux example: "/dev/ttyUSB0"
# macOS example: "/dev/tty.usbserial-110"

BAUD_RATE = 9600
LOG_FILE = "energy_log.txt"
# ---------------------------------------

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"Connected to {SERIAL_PORT}")
except Exception as e:
    print("Error opening serial port:", e)
    exit()

# Open the file once
with open(LOG_FILE, "a") as log:
    print("Logging started. Press CTRL+C to stop.")

    while True:
        try:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            
            if line:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                entry = f"{timestamp};{line}"
                
                print(entry)
                log.write(entry + "\n")
                log.flush()   # ensure data is written immediately

        except KeyboardInterrupt:
            print("\nLogging stopped.")
            break
        except Exception as e:
            print("Error:", e)
            time.sleep(1)
