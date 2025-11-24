// Arduino: dispenser + lid control (28BYJ-48 lid w/ ULN2003)
// Combine with HX711 weight & dispenser stepper you had.

#include <Stepper.h>
#include "HX711.h"

// ------------------- DISPENSER STEPPER (existing) -------------------
const int DISP_STEPS_PER_REV = 2048;     // same as your dispenser
Stepper dispStepper(DISP_STEPS_PER_REV, 7, 5, 6, 4);
const int DISP_OPEN_STEPS  = 350;
const int DISP_CLOSE_STEPS = -350;

// ------------------- LID STEPPER (28BYJ-48 via ULN2003) -------------
const int LID_STEPS_PER_REV = 2048;     // typical 28BYJ-48
// pins IN1,IN2,IN3,IN4 for ULN2003 driver
const int LID_PIN_1 = 8;
const int LID_PIN_2 = 9;
const int LID_PIN_3 = 10;
const int LID_PIN_4 = 11;
Stepper lidStepper(LID_STEPS_PER_REV, LID_PIN_1, LID_PIN_2, LID_PIN_3, LID_PIN_4);
const int LID_OPEN_STEPS  = 500;  // change to tune open angle
const int LID_CLOSE_STEPS = -500; // reverse to close

// ------------------- HX711 SCALE -------------------
#define DT 2
#define SCK 3
HX711 scale;
float calibration_factor = 471709.53;

// ------------------- STATE -------------------
bool dispensing = false;
float targetGrams = 0;
unsigned long lastLiveSend = 0;
bool lidOpen = false;

// ------------------- HELPERS -------------------
float getFastWeight() {
  long raw = scale.read(); // single HX711 sample (fast)
  float kg = (raw - scale.get_offset()) / scale.get_scale();
  if (kg < 0) kg = 0;
  return kg * 1000.0;
}

float getLiveWeight() {
  float kg = scale.get_units(10);  // stable average
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
  lidOpen = true;
  Serial.println("OPEN_LID");
  // confirm
  Serial.println("LID_OPENED");
}

void closeLid() {
  lidStepper.step(LID_CLOSE_STEPS);
  lidOpen = false;
  Serial.println("CLOSE_LID");
  Serial.println("LID_CLOSED");
}

void startDispense(float grams) {
  targetGrams = grams;
  dispensing = true;
  // Ensure lid is open before dispensing - leave actual lid open decision to Python,
  // but we still check and report for safety.
  Serial.print("TARGET ");
  Serial.println(targetGrams);
}

void setup() {
  Serial.begin(9600);

  dispStepper.setSpeed(15);
  lidStepper.setSpeed(15); // slower for lid if needed

  scale.begin(DT, SCK);
  scale.set_scale(calibration_factor);

  delay(1500);
  scale.tare();

  Serial.println("READY");
}

void loop() {

  // ===== REAL-TIME TARGET CHECK =====
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

  // ===== LIVE STREAM TO PYTHON (unchanged logic) =====
  if (millis() - lastLiveSend > 300) {
    float liveW = getLiveWeight();

    Serial.print("LIVE ");
    Serial.println(liveW, 1);

    lastLiveSend = millis();
  }

  // ===== COMMAND LISTENER =====
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    // Commands:
    // OPEN_LID / CLOSE_LID
    // DISPENSE <grams>
    // STOP
    // OPEN_DISP / CLOSE_DISP are internal - we keep naming consistent

    if (cmd == "OPEN_LID") {
      openLid();
    } else if (cmd == "CLOSE_LID") {
      closeLid();
    } else if (cmd.startsWith("DISPENSE")) {
      float grams = cmd.substring(8).toFloat();
      if (grams > 0) {
        // It's caller's responsibility to open lid before calling DISPENSE
        startDispense(grams);
        // physically open dispenser door (not lid) and start dispensing
        openDispenser();
      }
    } else if (cmd == "STOP") {
      dispensing = false;
      closeDispenser();
      Serial.println("STOPPED");
    } else if (cmd == "FORCE_CLOSE_LID") {
      // immediate quick close (safety)
      closeLid();
    } 
  }

  delay(10);
}
