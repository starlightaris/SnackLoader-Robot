#include "arduino_secrets.h"

const int TRIG = 6;
const int ECHO = 7;

void setup() {
  Serial.begin(9600);//test//test//test
  pinMode(TRIG, OUTPUT);
  pinMode(ECHO, INPUT);
  digitalWrite(TRIG, LOW);
  
  Serial.println("ULTRASONIC_READY");
}

void loop() {
  
  int dist = getDistance();
  
  Serial.println(dist);
  
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "TRIGGER") {
      Serial.println("ACTION_TRIGGERED");
    }
  }
  delay(200);
}

int getDistance() {
  
  digitalWrite(TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG, LOW);
  
  long duration = pulseIn(ECHO, HIGH, 30000);
  
  if (duration == 0) {
    return 999; // Return 999 if timeout (no object detected)
  }
  
  // distance in cm
  return duration * 0.034 / 2;
}

