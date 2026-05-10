const int sensorPin = A0;
const int pulsesPerKWh = 1000;

// Hysteresis: separate thresholds prevent false re-triggering near the boundary
const int thresholdHigh = 750;  // rising edge: LED turns on
const int thresholdLow  = 650;  // falling edge: LED turns off

// Minimum pulse duration (ms) — filters out sub-5ms noise spikes
const unsigned long minPulseMs = 5;

// If no pulse arrives within this window, report 0 kW (5 minutes)
const unsigned long noPulseTimeoutMs = 300000UL;

bool lightOn = false;
unsigned long lightOnTime = 0;

unsigned long pulseCount = 0;
unsigned long lastPulseTime = 0;
float instantPowerKw = 0.0;

unsigned long lastCalcTime = 0;
const unsigned long calcInterval = 60000;

void setup() {
  Serial.begin(9600);
  lastCalcTime = millis();
}

void loop() {
  int val = analogRead(sensorPin);
  unsigned long now = millis();

  if (!lightOn && val > thresholdHigh) {
    // Rising edge detected
    lightOn = true;
    lightOnTime = now;
  } else if (lightOn && val < thresholdLow) {
    // Falling edge — only count if pulse lasted long enough to not be noise
    if (now - lightOnTime >= minPulseMs) {
      pulseCount++;

      // Instantaneous power from time between consecutive pulses
      if (lastPulseTime > 0) {
        unsigned long intervalMs = now - lastPulseTime;
        instantPowerKw = 3600000.0 / ((float)intervalMs * pulsesPerKWh);
      }
      lastPulseTime = now;
    }
    lightOn = false;
  }

  if (now - lastCalcTime >= calcInterval) {
    unsigned long elapsed = now - lastCalcTime;
    lastCalcTime = now;

    unsigned long pulses = pulseCount;
    pulseCount = 0;

    float avgPowerKw;
    if (pulses == 0 || (lastPulseTime > 0 && (now - lastPulseTime) > noPulseTimeoutMs)) {
      avgPowerKw = 0.0;
      instantPowerKw = 0.0;
    } else {
      // Use actual elapsed time rather than assuming exactly 60 000 ms
      float pulsesPerHour = pulses * (3600000.0 / (float)elapsed);
      avgPowerKw = pulsesPerHour / pulsesPerKWh;
    }

    Serial.print(val);
    Serial.print(";");
    Serial.print(pulses);
    Serial.print(";");
    Serial.print(avgPowerKw, 3);
    Serial.print(";");
    Serial.print(instantPowerKw, 3);
    Serial.println("");
  }
}
