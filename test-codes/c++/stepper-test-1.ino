#include <Stepper.h>

const int STEPS_PER_REVOLUTION = 2048;

// Pin connections: IN1, IN3, IN2, IN4
Stepper bowlStepper(STEPS_PER_REVOLUTION, 11, 9, 10, 8);
Stepper dispenserStepper(STEPS_PER_REVOLUTION, 7, 5, 6, 4);

void setup() {
  // 10 RPM
  bowlStepper.setSpeed(10);
  dispenserStepper.setSpeed(10);
  
  Serial.begin(9600);
  Serial.println("Stepper Motors Ready!");
}

void loop() {
  // Move both motors 90 degrees forward
  Serial.println("Moving 90 degrees FORWARD");
  
  int steps90 = STEPS_PER_REVOLUTION / 4;   // (2048 = 360 degree, 1024 = 180, 512 = 90)
  
  bowlStepper.step(steps90);
  dispenserStepper.step(steps90);
  
  delay(1000);  // 1s
  
  // Move both motors 90 degrees backward
  Serial.println("Moving 90 degrees BACKWARD");
  
  bowlStepper.step(-steps90);
  dispenserStepper.step(-steps90);
  
  delay(2000);
}