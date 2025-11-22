 #include "HX711.h"

#define DT 2   
#define SCK 3  

HX711 scale;


float calibration_factor = 411936.0;

void setup() {
  Serial.begin(9600);
  scale.begin(DT, SCK);

  scale.set_scale(calibration_factor);

  delay(1000);
  Serial.println("Make sure NO weight is on the scale...");
  delay(1500);

  scale.tare();   

  Serial.println("Scale ready.");
}

void loop() {
  
  float weightKg = scale.get_units(10);

  if (weightKg < 0) weightKg = 0;

  
  float weightGrams = weightKg * 1000.0;

  
  Serial.print(weightGrams, 1);   
  Serial.println(" DOG");

  delay(30);
}
