#include "DHT.h"

#define DHTPIN 15
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();
  Serial.println("DHT11 Sensor Test");
}

void loop() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  if (isnan(h) || isnan(t)) {
    Serial.println("Sensor Error!");
    return;
  }

  Serial.print("Temperature: ");
  Serial.print(t);
  Serial.print(" °C | Humidity: ");
  Serial.print(h);
  Serial.println(" %");

  delay(1000);
}
