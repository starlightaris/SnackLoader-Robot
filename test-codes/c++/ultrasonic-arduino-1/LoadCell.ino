#include "HX711.h"

#define DT 3   // HX711 DT pin connected to Arduino pin 3
#define SCK 2  // HX711 SCK pin connected to Arduino pin 2

HX711 scale;

// 👉 Use a POSITIVE calibration factor
float calibration_factor = 7050;   // Change this after calibration

void setup() {
  Serial.begin(9600);
  scale.begin(DT, SCK);

  scale.set_scale(calibration_factor);
  scale.tare();   // Reset the scale to 0

  Serial.println("Scale ready...");
}

void loop() {
  // Read weight using average of 10 samples
  float weight = scale.get_units(10);

  // Convert negative noise values to positive
  if (weight < 0) {
    weight = -weight;
  }

  Serial.print("Weight: ");
  Serial.print(weight, 3); // Show 3 decimal places
  Serial.println(" kg");

  delay(300);
}
