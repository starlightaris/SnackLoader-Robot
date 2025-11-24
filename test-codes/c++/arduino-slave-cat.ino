#include <Stepper.h>
#include "HX711.h"

// Stepper motor setup
const int STEPS_PER_REVOLUTION = 2048;
Stepper bowlStepper(STEPS_PER_REVOLUTION, 11, 9, 10, 8);
Stepper dispenserStepper(STEPS_PER_REVOLUTION, 7, 5, 6, 4);

// Load cell setup
HX711 scale;
const int LOADCELL_DOUT_PIN = 2;
const int LOADCELL_SCK_PIN = 3;
float currentWeight = 0;
float maxWeight = 0;  // Set by RPi
float calibration_factor = -415; // Calibrate for your load cell

int steps90 = STEPS_PER_REVOLUTION / 4;

// Motor states
bool bowlOpen = false;
bool dispenserOpen = false;

// Dispensing control
bool isDispensing = false;

void setup() {
  bowlStepper.setSpeed(10);
  dispenserStepper.setSpeed(10);
  
  // Load cell initialization
  scale.begin(LOADCELL_DOUT_PIN, LOADCELL_SCK_PIN);
  scale.set_scale(calibration_factor);
  scale.tare();
  
  Serial.begin(9600);
  Serial.println("System Ready!");
  Serial.println("Commands: 'DISPENSE', 'CAT', 'CLOSE_ALL', 'WEIGHT', 'MAX_WEIGHT:[value]'");
  
  closeAll();
}

void loop() {
  // Read current weight
  if (scale.is_ready()) {
    currentWeight = scale.get_units(3); // Average 3 readings
    if (currentWeight < 0) currentWeight = 0; // Prevent negative weights
  }
  
  // Check if max weight reached during dispensing
  if (isDispensing && currentWeight >= maxWeight && maxWeight > 0) {
    Serial.println("Max weight reached - closing dispenser");
    closeDispenser();
    isDispensing = false;
  }
  
  // Process serial commands
  if (Serial.available() > 0) {
    processSerialCommand();
  }
  
  delay(100);
}

void processSerialCommand() {
  String command = Serial.readStringUntil('\n');
  command.trim();
  
  Serial.print("Received: ");
  Serial.println(command);
  
  if (command == "DISPENSE") {
    startDispensing();
  }
  else if (command == "CAT") {
    petDetected();
  }
  else if (command == "CLOSE_ALL") {
    closeAll();
    isDispensing = false;
  }
  else if (command == "WEIGHT") {
    sendWeight();
  }
  else if (command.startsWith("MAX_WEIGHT:")) {
    setMaxWeight(command);
  }
  else {
    Serial.println("Unknown command");
  }
}

void startDispensing() {
  if (maxWeight <= 0) {
    Serial.println("Error: Max weight not set. Use MAX_WEIGHT:[value] first");
    return;
  }
  
  Serial.println("Starting food dispensing");
  Serial.print("Target weight: ");
  Serial.println(maxWeight);
  
  // Open both lids
  openBowl();
  openDispenser();
  
  isDispensing = true;  
  Serial.println("Dispensing started - dispenser will auto-close when max weight reached");
}

void petDetected() {
  Serial.println("Pet detected - opening bowl");
  openBowl();
}

void setMaxWeight(String command) {
  String weightStr = command.substring(11); // Remove "MAX_WEIGHT:"
  maxWeight = weightStr.toFloat();
  Serial.print("Max weight set to: ");
  Serial.println(maxWeight);
}

void openBowl() {
  if (!bowlOpen) {
    Serial.println("Opening bowl lid...");
    bowlStepper.step(steps90);
    bowlOpen = true;
    Serial.println("Bowl open");
  }
}

void closeBowl() {
  if (bowlOpen) {
    Serial.println("Closing bowl lid...");
    bowlStepper.step(-steps90);
    bowlOpen = false;
    Serial.println("Bowl closed");
  }
}

void openDispenser() {
  if (!dispenserOpen) {
    Serial.println("Opening dispenser lid...");
    dispenserStepper.step(steps90);
    dispenserOpen = true;
    Serial.println("Dispenser open");
  }
}

void closeDispenser() {
  if (dispenserOpen) {
    Serial.println("Closing dispenser lid...");
    dispenserStepper.step(-steps90);
    dispenserOpen = false;
    Serial.println("Dispenser closed");
  }
}

void closeAll() {
  Serial.println("Closing all lids");
  closeBowl();
  closeDispenser();
  Serial.println("All lids closed");
}

void sendWeight() {
  Serial.print("CURRENT_WEIGHT:");
  Serial.println(currentWeight, 2);
  Serial.print("MAX_WEIGHT:");
  Serial.println(maxWeight, 2);
  Serial.print("DISPENSING:");
  Serial.println(isDispensing ? "ACTIVE" : "INACTIVE");
}