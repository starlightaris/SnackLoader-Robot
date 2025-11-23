#include <Stepper.h>
#include "HX711.h"


const int stepsPerRevolution = 2048;
Stepper stepper(stepsPerRevolution, 7, 6, 5, 4);

float currentAngle = 0;   

#define DT 2
#define SCK 3

HX711 scale;
float calibration_factor = 471709.53;  


bool targetOpen = false;      
float targetGrams = 0;        
bool autoCloseTriggered = false;

float tolerance = 3.0;        

void setup() {
  Serial.begin(9600);
  stepper.setSpeed(10);

  
  scale.begin(DT, SCK);
  scale.set_scale(calibration_factor);

  delay(1000);
  Serial.println("Make sure NO weight is on the scale now...");
  delay(1500);
  
  scale.tare();

  Serial.println("\nDISPENSER CONTROL READY");
  Serial.println("Enter: true 200  -> to OPEN and set 200g target");
  Serial.println("Enter: false 0   -> to CLOSE");
}

void loop() {

  
  float weightKg = scale.get_units(50);
  if (weightKg < 0) weightKg = 0;

  float weightGrams = weightKg * 1000.0;

  Serial.print("Weight: ");
  Serial.print(weightGrams, 1);
  Serial.println(" g");

  
  if (targetOpen == true && targetGrams > 0) {

    if (!autoCloseTriggered) {
      
      float minReach = targetGrams - tolerance;
      float maxReach = targetGrams + tolerance;

      if (weightGrams >= minReach && weightGrams <= maxReach) {
        Serial.println("TARGET WEIGHT REACHED! Auto-closing lid...");
        closeLid();
        autoCloseTriggered = true;
      }
    }
  }

  
  if (Serial.available() > 0) {

    String input = Serial.readStringUntil('\n');
    input.trim();
    input.toLowerCase();

    int spaceIndex = input.indexOf(' ');
    if (spaceIndex < 0) {
      Serial.println("Invalid format! Use: true 200");
      return;
    }

    String boolPart = input.substring(0, spaceIndex);
    String gramPart = input.substring(spaceIndex + 1);

    
    if (boolPart == "true") {
      targetOpen = true;
    }
    else if (boolPart == "false") {
      targetOpen = false;
    }
    else {
      Serial.println("Invalid boolean! Use true or false.");
      return;
    }

    
    targetGrams = gramPart.toFloat();
    autoCloseTriggered = false;

   
    if (targetOpen == true) {
      openLid();
      Serial.print("Target grams set: ");
      Serial.println(targetGrams);
    }
    else {
      closeLid();
      targetGrams = 0;
    }
  }

  delay(80);
}


void openLid() {
  if (currentAngle == 60) {
    Serial.println("LID ALREADY OPEN");
    return;
  }

  Serial.println("Opening lid...");
  moveToAngle(60);
  currentAngle = 60;
  Serial.println("STATUS: true (OPEN)");
}

void closeLid() {
  if (currentAngle == 0) {
    Serial.println("LID ALREADY CLOSED");
    return;
  }

  Serial.println("Closing lid...");
  moveToAngle(0);
  currentAngle = 0;
  Serial.println("STATUS: false (CLOSED)");
}

void moveToAngle(float targetAngle) {
  float diff = targetAngle - currentAngle;
  int stepsToMove = (2048.0 * diff) / 360.0;
  stepper.step(stepsToMove);
}
