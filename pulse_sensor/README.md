# Pulse Sensor

Reads the energy meter's LED pulses via an LDR on a Seeeduino XIAO (SAMD21)
and streams consumption data to a Raspberry Pi over serial.

## Hardware

- Seeeduino XIAO (SAMD21)
- LDR (Light Dependent Resistor) + 10 kΩ pull-down resistor wired to pin `A0`

### Wiring — XIAO to Raspberry Pi

| XIAO pin | Raspberry Pi pin | Purpose |
|---|---|---|
| 5V | Pin 2 or 4 (5V) | Power |
| GND | Pin 6 (GND) | Ground |
| TX (pad 6) | Pin 10 (GPIO15 / RX) | Serial data to Pi |

> USB is only needed for flashing. Disconnect USB and use the wiring above for normal operation.

## Software setup

### 1. Install arduino-cli

```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
```

### 2. Add the Seeed SAMD board package

```bash
arduino-cli config add board_manager.additional_urls \
  https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json

arduino-cli core update-index
arduino-cli core install Seeeduino:samd
```

### 3. Fix serial port permissions (Linux / Raspberry Pi OS)

```bash
sudo usermod -a -G dialout $USER
newgrp dialout
```

## Compile

```bash
arduino-cli compile --fqbn Seeeduino:samd:seeed_XIAO_m0 pulse_sensor
```

## Upload

Connect the XIAO via USB, then:

```bash
arduino-cli upload -p /dev/ttyACM0 --fqbn Seeeduino:samd:seeed_XIAO_m0 pulse_sensor
```

If the port is not `/dev/ttyACM0`, find the correct one with:

```bash
arduino-cli board list
```

## Serial output format

The sketch emits one line per minute over serial (9600 baud):

```
<LDR>;<pulses/min>;<avg_kW>;<instant_kW>
```

| Field | Description |
|---|---|
| LDR | Raw analog reading (0–1023) at report time |
| pulses/min | Pulse count in the last minute |
| avg_kW | Average power calculated from pulses/min |
| instant_kW | Instantaneous power from last inter-pulse interval |

Example:

```
45;14;0.840;0.923
```

## Running the logger

After flashing, disconnect USB and use the UART wiring above. Then on the Pi:

```bash
# UART via GPIO pins (normal operation)
python3 read_energy.py   # edit SERIAL_PORT = "/dev/ttyS0" inside the file

# USB (for testing/debugging)
python3 read_energy.py   # keep SERIAL_PORT = "/dev/ttyACM0"
```

Log entries are appended to `energy_log.txt` in the format:

```
datetime;LDR;pulses/min;avg_kW;instant_kW
```

## Adjusting the LDR threshold

The XIAO uses a 12-bit ADC (0–4095). Default thresholds are 3000 (high) and 2600 (low).

If pulses are not detected reliably, adjust `thresholdHigh` and `thresholdLow`
in `pulse_sensor.ino`. Monitor the raw LDR value in the serial output:
- Ambient (no flash): note the baseline value
- During flash: note the peak value
- Set `thresholdHigh` ~halfway between baseline and peak, `thresholdLow` slightly below that
