# ele_monitor

## Quick build

Compile and deploy everything in one command:

```bash
./build.sh
```

This will:
1. Compile and upload the pulse sensor firmware to the Seeeduino XIAO (USB)
2. Compile and upload ele_monitor2 to the MKR WiFi 1010 (WiFi OTA)
3. Restart the web app service

## Manual build commands

### ele_monitor2 (MKR WiFi 1010)

```bash
arduino-cli compile --fqbn arduino:samd:mkrwifi1010 ele_monitor2
arduino-cli upload -p /dev/ttyACM1 --fqbn arduino:samd:mkrwifi1010 ele_monitor2
arduino-cli upload -p 192.168.50.131 --fqbn arduino:samd:mkrwifi1010 ele_monitor2
```

### Pulse sensor (Seeeduino XIAO)

See `pulse_sensor/README.md` for compile and upload instructions.

## Configuration

Create `arduino_secrets.h` with your credentials:

```cpp
#define SECRET_SSID "wifi_name"
#define SECRET_PASS "wifi_password"
#define SECRET_SERVER "server_ip"
```

See `arduino_secrets.example.h` for reference.
