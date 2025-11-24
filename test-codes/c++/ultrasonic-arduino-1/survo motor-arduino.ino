#include <Servo.h>

Servo feederServo;

void setup() {
  feederServo.attach(18);  
}

void loop() {
  feederServo.write(0);
  delay(1000);

  feederServo.write(90);
  delay(1000);

  feederServo.write(180);
  delay(1000);
}
