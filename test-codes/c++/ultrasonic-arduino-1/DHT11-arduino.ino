#include "DHT.h"

#define DHTPIN 4      
#define DHTTYPE DHT11   

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(9600);
  dht.begin();
  Serial.println("DHT11 Test Starting...");
}

void loop() {
  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature(); 
  float temperatureF = dht.readTemperature(true); 

 
  if (isnan(humidity) || isnan(temperature)) {
    Serial.println("Failed to read from DHT11 sensor!");
    return;
  }

  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.print(" %\t");

  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.print(" °C  |  ");

  Serial.print(temperatureF);
  Serial.println(" °F");

  delay(2000); 
