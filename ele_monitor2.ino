/*

DOCS
 */

#include <SPI.h>
#include <WiFiNINA.h>
#include <ArduinoOTA.h>
#include <ArduinoJson.h>
#include <ArduinoHttpClient.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include "arduino_secrets.h"

/////// Wifi Settings ///////
char ssid[] = SECRET_SSID;      // your network SSID (name)
char pass[] = SECRET_PASS;   // your network password
char server[] = SECRET_SERVER;
int status = WL_IDLE_STATUS;
const int port = SECRET_PORT;
unsigned long interval;
unsigned long startMillis;

WiFiClient wifi_client;
HttpClient http_client = HttpClient(wifi_client, server, port);
LiquidCrystal_I2C lcd(0x3F, 16, 2);

void setup() {
  pinMode(3, OUTPUT);
  pinMode(4, OUTPUT);
  pinMode(5, OUTPUT);

  digitalWrite(3, HIGH);
  digitalWrite(4, HIGH);
  digitalWrite(5, HIGH);

  lcd.init();
  lcd.backlight();

  lcd.setCursor(0,0);
  lcd.print("Alustetaan...");

  //Initialize serial:
  Serial.begin(9600);

  // check for the presence of the shield:
  if (WiFi.status() == WL_NO_SHIELD) {
    Serial.println("WiFi shield not present");
    // don't continue:
    while (true);
  }

  // attempt to connect to Wifi network:
  while ( status != WL_CONNECTED) {
    Serial.print("Attempting to connect to SSID: ");
    Serial.println(ssid);
    // Connect to WPA/WPA2 network. Change this line if using open or WEP network:
    status = WiFi.begin(ssid, pass);
  }

  // start the WiFi OTA library with internal (flash) based storage
  ArduinoOTA.begin(WiFi.localIP(), "Arduino", "password", InternalStorage);


  // you're connected now, so print out the status:
  printWifiStatus();
  interval = 60000;
  startMillis = millis();
}

void loop() {
  // check for WiFi OTA updates
  ArduinoOTA.poll();
  unsigned long currentMillis = millis();

  if(currentMillis >= interval) {
    Serial.println("making GET request");
    http_client.get("/api");
    // read the status code and body of the response
    int statusCode = http_client.responseStatusCode();
    if (statusCode == 200) {
      String response = http_client.responseBody();
      //Serial.println(statusCode);
      //Serial.println(response);
      // Parse the JSON payload
      DynamicJsonDocument doc(1024);  // Create a JSON document (ensure enough space)
      DeserializationError error = deserializeJson(doc, response);
      // Check for parsing errors
      if (error) {
        Serial.print("Failed to parse JSON: ");
        Serial.println(error.f_str());
      }
      // Access data in the JSON (example: assuming a "title" field in the JSON)
      const char* current_time = doc["current_time"];
      const float current_price = doc["current_price"];
      const int green_led = doc["green_led"];
      const int red_led = doc["red_led"];
      const int yellow_led = doc["yellow_led"];
      const float power = doc["power"];
      const float power_price = doc["kwh_price"];
      //LCD
      lcd.setCursor(0,0);
      lcd.print("Hinta nyt:  ");
      lcd.print(current_price);
      lcd.setCursor(0,1);
      lcd.print("kW: ");
      lcd.print(power);
      digitalWrite(3, green_led);
      digitalWrite(4, yellow_led);
      digitalWrite(5, red_led);
    } else {
      lcd.setCursor(0,0);
      lcd.print("HTTP error ");
      lcd.print(statusCode);
    }
    interval = interval + 60000;
  }
}

void printWifiStatus() {
  // print the SSID of the network you're attached to:
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());

  // print your WiFi shield's IP address:
  IPAddress ip = WiFi.localIP();
  Serial.print("IP Address: ");
  Serial.println(ip);

  // print the received signal strength:
  long rssi = WiFi.RSSI();
  Serial.print("signal strength (RSSI):");
  Serial.print(rssi);
  Serial.println(" dBm");
}
