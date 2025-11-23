#include <Stepper.h>
#include "HX711.h"

// ------------------- STEPPER (DISPENSER ONLY) -------------------
const int STEPS_PER_REV = 2048;
Stepper dispStepper(STEPS_PER_REV, 7, 5, 6, 4);

const int OPEN_STEPS  = 350;   // adjust for your feeder
const int CLOSE_STEPS = -350;  // reverse direction

// ------------------- HX711 SCALE -------------------
#define DT 2
#define SCK 3
HX711 scale;

float calibration_factor = 471709.53;

// ------------------- STATE -------------------
bool dispensing = false;
float targetGrams = 0;
unsigned long lastLiveSend = 0;


// ---------------- FAST SAMPLE (for closing) ----------------
float getFastWeight() {
  long raw = scale.read(); // single HX711 sample (fast)
  float kg = (raw - scale.get_offset()) / scale.get_scale();
  if (kg < 0) kg = 0;
  return kg * 1000.0;
}


// ---------------- SMOOTH SAMPLE (for live streaming) --------
float getLiveWeight() {
  float kg = scale.get_units(10);  // stable average
  if (kg < 0) kg = 0;
  return kg * 1000.0;
}


// ---------------- STEPPER CONTROL ----------------
void openDispenser() {
  dispStepper.step(OPEN_STEPS);
  Serial.println("OPEN_DISP");
}

void closeDispenser() {
  dispStepper.step(CLOSE_STEPS);
  Serial.println("CLOSED_DISP");
}


// ---------------- START DISPENSING ----------------
void startDispense(float grams) {
  targetGrams = grams;
  dispensing = true;

  openDispenser();

  Serial.print("TARGET ");
  Serial.println(targetGrams);
}


// ---------------- SETUP ----------------
void setup() {
  Serial.begin(9600);

  dispStepper.setSpeed(15);

  scale.begin(DT, SCK);
  scale.set_scale(calibration_factor);

  delay(1500);
  scale.tare();

  Serial.println("READY");
}


// ---------------- MAIN LOOP ----------------
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

    if (cmd.startsWith("DISPENSE")) {
      float grams = cmd.substring(8).toFloat();
      if (grams > 0) {
        startDispense(grams);
      }
    }

    if (cmd == "STOP") {
      dispensing = false;
      closeDispenser();
      Serial.println("STOPPED");
    }
  }

  delay(10);
}
