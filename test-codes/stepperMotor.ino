#include "AFMotor_R4.h"

// 28BYJ-48 stepper: 2048 steps per full rotation
// Motor connected to M3 & M4 → PORT 2 on L293D shield
AF_Stepper motor(2048, 2);

void setup() {
  Serial.begin(9600);
  Serial.println("Stepper Angle Control Test");

  motor.setSpeed(15);  // Speed in RPM
}

// Rotate to any angle
void rotateAngle(float angle, int direction, uint8_t style) {
  int steps = (2048.0 * angle) / 360.0;  // convert angle → steps
  motor.step(steps, direction, style);
}

void loop() {

  Serial.println("Rotating 90 degrees CW");
  rotateAngle(90, FORWARD, DOUBLE);
  delay(1000);

  Serial.println("Rotating 45 degrees CCW");
  rotateAngle(45, BACKWARD, DOUBLE);
  delay(1000);

  Serial.println("Rotating 180 degrees CW");
  rotateAngle(180, FORWARD, DOUBLE);
  delay(1000);
}
