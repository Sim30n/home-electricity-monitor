const int sensorPin = A0;
const int pulsesPerKWh = 1000;   // Your meter LED pulses per kWh

int threshold = 700;             // Adjust after testing
bool lightOn = false;

volatile unsigned long pulseCount = 0;

unsigned long lastCalcTime = 0;
const unsigned long calcInterval = 60000; // one minute

void setup() {
  Serial.begin(9600);
}

void loop() {
  int val = analogRead(sensorPin);

  // Detect rising light (LED flash)
  if (val > threshold && !lightOn) {
    lightOn = true;
    pulseCount++;
  }

  // Detect falling light (end of flash)
  if (val <= threshold && lightOn) {
    lightOn = false;
  }

  // Calculate every minute
  if (millis() - lastCalcTime >= calcInterval) {
    lastCalcTime = millis();

    unsigned long pulses = pulseCount;
    pulseCount = 0;

    // Pulses/min → pulses/hour
    float pulsesPerHour = pulses * 60.0;

    // Convert to kW
    float kW = pulsesPerHour / pulsesPerKWh;

    //Serial.print("");
    Serial.print(val);
    Serial.print(";");
    Serial.print(pulses);
    Serial.print(";");
    Serial.print(kW, 3);
    Serial.println("");
  }
}

