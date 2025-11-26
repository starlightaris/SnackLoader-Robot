#include "HX711.h"

#define DOUT  4  
#define CLK   4 

HX711 scale;

float calibration_factor = -10500;  
//  after calibration

void setup() {
  Serial.begin(9600);
  Serial.println("HX711 Load Cell Test");

  scale.begin(DOUT, CLK);

  delay(1000);

  Serial.println("Remove all weight...");
  scale.tare(); 
  Serial.println("Scale tared!");
}

void loop() {
  if (scale.is_ready()) {
    long reading = scale.get_units(5);  

    Serial.print("Weight: ");
    Serial.print(reading);
    Serial.println(" g");
  } else {
    Serial.println("HX711 not found.");
  }

  delay(500);
}
