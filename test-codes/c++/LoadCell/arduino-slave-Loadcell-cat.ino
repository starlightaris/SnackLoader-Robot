#include "HX711.h"

#define DT 2
#define SCK 3

HX711 scale;

float calibration_factor = 471709.53;

void setup() {
  Serial.begin(9600);
  scale.begin(DT, SCK);

  scale.set_scale(calibration_factor);
  delay(1000);

  Serial.println("Make sure NO weight is on the scale now...");
  delay(1500);

  scale.tare(); // Zero scale

  Serial.println("Scale ready…");
}

void loop() {
  float weightKg = scale.get_units(50);

  if (weightKg < 0) weightKg = 0;

  float weightGrams = weightKg * 1000.0;

  // IMPORTANT: clean number only
  Serial.println(weightGrams, 1);

  delay(50);
}
