#include <WiFi.h>
#include "HX711.h"
#include <PubSubClient.h>
#include <Wire.h>
#include <SPI.h>
#include "time.h"

#define DOUT  4   // HX711 DT
#define CLK   5   // HX711 SCK
#define PUMP_PIN 16
#define MAX_WATER_ML 100.0
#define REFILL_THRESHOLD 99.0  // when to trigger refill
#define SAMPLE_COUNT 5
#define SAFETY_TIMEOUT_MS 10000 // 10s max pump run

// WiFi / MQTT
const char* ssid = " test@gmail.com";
const char* password = "test123";
const char* mqtt_server = "broker.hivemq.com"; // example public broker

HX711 scale;
WiFiClient espClient;
PubSubClient client(espClient);

float dailyUsed = 0;
float scale_factor = 215.0; // set from calibration
long lastMidnight = 0;

void setup_wifi() {
  delay(10);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PUMP_PIN, OUTPUT);
  digitalWrite(PUMP_PIN, LOW); // pump off

  scale.begin(DOUT, CLK);
  scale.set_scale(scale_factor);
  scale.tare();

  setup_wifi();
  client.setServer(mqtt_server, 1883);

  // optional: sync time (for daily reset) using NTP
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  delay(2000);
  syncMidnight();
}

void reconnect() {
  while (!client.connected()) {
    if (client.connect("esp32-pet-water")) {
      // connected
    } else {
      delay(2000);
    }
  }
}

float read_ml() {
  // median/average of multiple reads
  long sum = 0;
  int n = SAMPLE_COUNT;
  float vals[n];
  for (int i=0;i<n;i++) {
    vals[i] = scale.get_units(3);
    delay(50);
  }
  // compute median to avoid spikes
  for (int i=0;i<n-1;i++) for(int j=i+1;j<n;j++) if(vals[j]<vals[i]) { float t=vals[i]; vals[i]=vals[j]; vals[j]=t; }
  float median = vals[n/2];
  if (median < 0) median = 0;
  return median; // grams -> ml approx
}

void syncMidnight(){
  struct tm timeinfo;
  if(getLocalTime(&timeinfo)){
    // compute timestamp for next midnight
    time_t now = time(NULL);
    timeinfo.tm_hour = 0; timeinfo.tm_min = 0; timeinfo.tm_sec = 0;
    time_t midnight = mktime(&timeinfo);
    if (midnight > now) lastMidnight = midnight;
    else lastMidnight = midnight + 24*3600;
  }
}

void checkMidnightReset(){
  time_t now = time(NULL);
  if (now >= lastMidnight) {
    // push yesterday value before reset
    publishDaily(dailyUsed);
    dailyUsed = 0;
    lastMidnight += 24*3600;
  }
}

void publishDaily(float val){
  if (!client.connected()) reconnect();
  char payload[64];
  snprintf(payload, sizeof(payload), "{\"dailyUsed\":%.2f}", val);
  client.publish("petwater/daily", payload);
}

void publishCurrent(float curr){
  if (!client.connected()) reconnect();
  char payload[64];
  snprintf(payload, sizeof(payload), "{\"current\":%.2f}", curr);
  client.publish("petwater/current", payload);
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  checkMidnightReset();

  float current = read_ml();
  publishCurrent(current);

  if (current < REFILL_THRESHOLD) {
    float refillAmount = MAX_WATER_ML - current;
    Serial.printf("Refilling: need %.2f ml\n", refillAmount);
    unsigned long start = millis();
    digitalWrite(PUMP_PIN, HIGH); // start pump
    // keep pumping until target or safety timeout
    while (millis() - start < SAFETY_TIMEOUT_MS) {
      float nowVal = read_ml();
      if (nowVal >= MAX_WATER_ML) break;
    }
    digitalWrite(PUMP_PIN, LOW);
    // after pump stops, read stable value
    delay(200);
    float finalVal = read_ml();
    float actualAdded = finalVal - current;
    if (actualAdded < 0) actualAdded = 0;
    dailyUsed += actualAdded;
    Serial.printf("Added %.2f ml, daily now %.2f\n", actualAdded, dailyUsed);
    publishDaily(dailyUsed);
  }

  delay(2000);
}
