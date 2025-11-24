#include <Stepper.h>
#include "HX711.h"

//  DISPENSER STEPPER
Stepper dispStepper(2048, 7, 5, 6, 4);
const int DISP_OPEN_STEPS  = 350;
const int DISP_CLOSE_STEPS = -350;

//  LID STEPPER
Stepper lidStepper(2048, 11, 9, 10, 8);
const int LID_OPEN_STEPS  = 500;
const int LID_CLOSE_STEPS = -500;

//  HX711 SCALE
#define DT 2
#define SCK 3
HX711 scale;
float calibration_factor = 471709.53;

//  STATE
bool dispensing = false;
float targetGrams = 0;
unsigned long lastLiveSend = 0;
bool lidStatus = false;

float getFastWeight() {
  long raw = scale.read();
  float kg = (raw - scale.get_offset()) / scale.get_scale();
  if (kg < 0) kg = 0;
  return kg * 1000.0;
}

float getLiveWeight() {
  float kg = scale.get_units(10);
  if (kg < 0) kg = 0;
  return kg * 1000.0;
}

void openDispenser() {
  dispStepper.step(DISP_OPEN_STEPS);
  Serial.println("OPEN_DISP");
}

void closeDispenser() {
  dispStepper.step(DISP_CLOSE_STEPS);
  Serial.println("CLOSED_DISP");
}

void openLid() {
  lidStepper.step(LID_OPEN_STEPS);
  lidStatus = true;
  Serial.println("OPEN_LID");
  Serial.println("LID_OPENED");
}

void closeLid() {
  lidStepper.step(LID_CLOSE_STEPS);
  lidStatus = false;
  Serial.println("CLOSE_LID");
  Serial.println("LID_CLOSED");
}

void startDispense(float grams) {
  targetGrams = grams;
  dispensing = true;
  if ( lidStatus == false){
    openLid();
  }
  Serial.print("TARGET ");
  Serial.println(targetGrams);
}

void setup() {
  Serial.begin(9600);

  dispStepper.setSpeed(15);
  lidStepper.setSpeed(15);

  scale.begin(DT, SCK);
  scale.set_scale(calibration_factor);

  delay(1500);
  scale.tare();

  Serial.println("READY");
}

void loop() {

  if (dispensing) {
    float fastW = getFastWeight();

    if (fastW >= targetGrams) {
      closeDispenser();
      dispensing = false;

      // final stable reading
      float finalW = getLiveWeight();

      Serial.println("DONE");
      Serial.print("WEIGHT ");
      Serial.println(finalW, 1);
    }
  }

  if (millis() - lastLiveSend > 300) {
    float liveW = getLiveWeight();

    Serial.print("LIVE ");
    Serial.println(liveW, 1);

    lastLiveSend = millis();
  }

  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    // Commands:
    // OPEN_LID / CLOSE_LID
    // DISPENSE <grams>
    // STOP
    // OPEN_DISP / CLOSE_DISP

    if (cmd == "OPEN_LID") {
      openLid();
    } else if (cmd == "CLOSE_LID") {
      closeLid();
    } else if (cmd.startsWith("DISPENSE")) {
      float grams = cmd.substring(8).toFloat();
      if (grams > 0) {
        startDispense(grams);
        openDispenser();
      }
    } else if (cmd == "STOP") {
      dispensing = false;
      closeDispenser();
      Serial.println("STOPPED");
    } else if (cmd == "FORCE_CLOSE_LID") {
      closeLid();
    } 
  }

  delay(10);
}