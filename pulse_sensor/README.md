# Pulse Sensor

Reads the energy meter's LED pulses via an LDR on a Seeeduino XIAO (SAMD21)
and streams consumption data to a Raspberry Pi over USB serial.

## Hardware

- Seeeduino XIAO (SAMD21)
- LDR (Light Dependent Resistor) + 10 kΩ pull-down resistor wired to pin `A0`
- Power the LDR voltage divider from the XIAO's **3.3V pin** — the ADC reference
  is 3.3V so the signal must not exceed it

### Wiring — XIAO to Raspberry Pi

| XIAO pin | Raspberry Pi pin | Purpose |
|---|---|---|
| 5V | Pin 2 or 4 (5V) | Power |
| GND | Pin 6 (GND) | Ground |
| USB | USB port | Serial data + flashing |

The XIAO connects to the Pi via USB for both firmware uploads and normal operation.

## Software setup

### 1. Install arduino-cli

```bash
curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
sudo mv ~/bin/arduino-cli /usr/local/bin/
```

### 2. Add the Seeed SAMD board package

```bash
arduino-cli config add board_manager.additional_urls \
  https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json

arduino-cli core update-index
arduino-cli core install Seeeduino:samd
```

### 3. Fix serial port permissions

```bash
sudo usermod -a -G dialout $USER
newgrp dialout
```

## Compile

```bash
arduino-cli compile --fqbn Seeeduino:samd:seeed_XIAO_m0 pulse_sensor
```

## Upload

```bash
arduino-cli upload -p /dev/ttyACM0 --fqbn Seeeduino:samd:seeed_XIAO_m0 pulse_sensor
```

Find the correct port if it differs:

```bash
arduino-cli board list
```

## Serial output format

The sketch emits one line every 10 seconds over serial (9600 baud):

```
<LDR>;<pulses>;<avg_kW>;<instant_kW>
```

| Field | Description |
|---|---|
| LDR | Peak analog reading seen during the 10-second window (0–4095) |
| pulses | Pulse count in the last 10 seconds |
| avg_kW | Average power extrapolated from pulse count |
| instant_kW | Instantaneous power from last inter-pulse interval |

Example at ~0.36 kW:

```
980;1;0.360;0.194
```

## Running the logger as a service

Install `read_energy.py` as a systemd service that starts on boot:

```bash
./create_service.sh
```

The service restarts automatically every 5 seconds if the XIAO disconnects.

Monitor live output:

```bash
journalctl -u read_energy -f
```

## Adjusting the LDR thresholds

Thresholds are tuned for observed hardware values (flash peak ~980, ambient ~90):

- `thresholdHigh = 500` — rising edge, ~50% of flash peak
- `thresholdLow  = 200` — falling edge, well above ambient (~90) to prevent noise re-triggering

To retune for different hardware, monitor the LDR column in the serial output:
- During a flash: peak will be high (~980 in the reference setup)
- No flash: peak stays near ambient (~90)
- Set `thresholdHigh` to ~50% of flash peak, `thresholdLow` to ~20% of flash peak
