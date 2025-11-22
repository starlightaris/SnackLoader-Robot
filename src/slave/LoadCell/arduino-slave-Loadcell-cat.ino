#include "HX711.h"

#define DT 2   
#define SCK 3  

HX711 scale;


float calibration_factor = 476474.27;

void setup() {
  Serial.begin(9600);
  scale.begin(DT, SCK);

  scale.set_scale(calibration_factor);

  delay(1000);       
  Serial.println("Make sure NO weight is on the scale now...");
  delay(1500);
  scale.tare();      

  Serial.print("Calibration factor set to: ");
  Serial.println(calibration_factor, 2);
  Serial.println("Place your test weight now.");
}

void loop() {
 
  float weightKg = scale.get_units(20);

  if (weightKg < 0.0001) weightKg = 0;

  Serial.print(weightKg, 3); 
  Serial.println(" kg");

  delay(500);
}
