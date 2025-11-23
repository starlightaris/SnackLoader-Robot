#include <Stepper.h>

const int stepsPerRevolution = 2048;   
Stepper stepper(stepsPerRevolution, 7, 6, 5, 4);

float currentAngle = 0;   

void setup() {
  Serial.begin(9600);
  stepper.setSpeed(10);

  Serial.println("DISPENSER CONTROL (Boolean Mode)");
  Serial.println("Type true  -> OPEN (60°)");
  Serial.println("Type false -> CLOSE (0°)");
}

void loop() {

  if (Serial.available() > 0) {

    
    String input = Serial.readStringUntil('\n');
    input.trim();
    input.toLowerCase();

    
    bool command;

    if (input == "true") {
      command = true;
    } 
    else if (input == "false") {
      command = false;
    }
    else {
      Serial.println("Invalid input! Type: true or false");
      return;
    }

    
    float targetAngle = (command == true) ? 60 : 0;

    
    float angleDifference = targetAngle - currentAngle;
    int stepsToMove = (2048.0 * angleDifference) / 360.0;

    Serial.print("Moving to angle: ");
    Serial.println(targetAngle);

    stepper.step(stepsToMove);
    currentAngle = targetAngle;

    
    if (command == true) {
      Serial.println("STATUS: true (DISPENSER OPEN)");
    } else {
      Serial.println("STATUS: false (DISPENSER CLOSED)");
    }

    Serial.println("Ready for next boolean: true / false");
  }
}
