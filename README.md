# 🐾 SnackLoader Robot

An IoT-enabled automatic pet feeder built using a Raspberry Pi 4, Arduino, and computer vision.
The system detects pets using a camera, dispenses a controlled amount of food using load cells and stepper motors, and sends feeding data to a web application.

---

## 📌 Project Overview

This project is designed for households with multiple pets (cat & dog) where food portions and access must be controlled individually. The system:

* Detects the pet using a camera and pretrained ML library
* Managing bowl access time based on pet presence
* Dispenses a predefined amount of food set by the user
* Monitoring food weight using load cells
* Prevents one pet from eating another pet’s food
* Sending feeding data to a cloud database for monitoring via a web app

---

## 🔁 System Workflow

1. Pet Detection: Raspberry Pi continuously monitors the camera feed and identifies the pet (cat or dog).
2. Pet Selection: Based on the detected pet, the Pi selects the corresponding Arduino controlling that pet’s feeder.
3. Feeding Schedule: The web app sends feeding parameters to the Pi:
 * Amount of food to dispense
 * Scheduled time to feed
6. Command Forwarding: Raspberry Pi forwards these commands to the selected Arduino via serial communication.
7. Dispensing Control (Arduino):
 * Opens the dispenser lid
 * Continuously monitors the load cell to measure dispensed food
 * Stops dispensing once the target weight is reached
6. Bowl Lid Management:
 * Bowl lid stays open for 20 minutes if the pet is present
 * If the pet is detected during this period, the 20-minute timer resets
 * Bowl lid closes once the pet leaves and timer expires
7. Data Feedback: Arduino sends current weight and dispensing status back to Raspberry Pi, which forwards the data to Firebase for monitoring.

---

## 🧠 Key Features

* 🐶🐱 **Pet Identification** (Cat vs Dog)
* 🍽️ **Two Separate Feeding Units** (one per pet)
* 🔒 **Stepper-controlled Bowl Lids** to prevent food theft
* ⚖️ **Load Cell + HX711** for precise portion control
* 🔄 **Stepper-controlled Dispenser & Bowl Flip**
* 📷 **Camera Integration with Raspberry Pi**
* 🔁 **Two-way communication** between Raspberry Pi and Arduino
* ⚡ **Non-blocking motor control** for smooth operation

---

## 🏗️ System Architecture

```
Camera ──> Raspberry Pi 4 ── Serial ──> Arduino
                    │                   │
                    │                   ├─ Stepper (Dispenser)
                    │                   ├─ Stepper (Bowl Lid)
                    │                   └─ Load Cell (HX711)
```

Each pet has:

* 1 Arduino
* 2 Stepper motors (Dispenser + Bowl Lid)
* 1 Load cell

---

## 🔧 Hardware Components

### Per Pet Unit

* Arduino Uno
* Raspberry Pi 4 (shared)
* 28BYJ-48 Stepper Motors (x2)
* ULN2003 Stepper Motor Drivers (x2)
* 5kg Load Cell
* HX711 Load Cell Amplifier
* Camera Module (USB Web Camera; shared)
* External 5V Power Supply

---

## 🧩 Software Stack

### Raspberry Pi

* Python
* OpenCV
* Object Detection Model (Cat vs Dog)
* Serial Communication (`pyserial`)
* Firebase

### Arduino

* AccelStepper
* HX711 Library
* Serial Command Interface

---

## 🔌 Communication Protocol

The Raspberry Pi communicates with Arduino using **serial commands**:

| Command         | Description                      |
| --------------- | -------------------------------- |
| `CAT`           | Correct pet detected → open bowl |
| `DISPENSE`      | Start dispensing food            |
| `MAX_WEIGHT:XX` | Set target weight in grams       |
| `WEIGHT`        | Request current bowl weight      |
| `TARE`          | Reset scale to zero              |
| `CLOSE_ALL`     | Close all lids (safety)          |

---

## ⚙️ Arduino Responsibilities

* Control bowl lid motor
* Control dispenser motor
* Read load cell values
* Stop dispensing when target weight is reached
* Execute commands from Raspberry Pi

---

## 🧪 Calibration & Setup

1. Power the system (use **external 5V supply** for motors)
2. Upload Arduino firmware
3. Tare the load cell (`TARE` command)
4. Calibrate HX711 using known weights
5. Configure camera & pet detection model on Raspberry Pi

---

## 🚨 Safety & Reliability

* Non-blocking motor control
* Weight-based auto-stop
* Manual override via `CLOSE_ALL`
* Noise-filtered load cell readings

---

## 📁 Repository Structure

```
snackloader-robot/
│
├── src/ 
│   ├── master/
│   │   ├── camera.py
│   │   ├── cat_feeder_controller.py
│   │   ├── dog_feeder_controller.py
│   │   └── temperature.py
│   |
|   └── slave/
|       ├── arduino-pet-slave.ino
|       └── arduino-temperature-slave.ino
|
├── Object_Detection_Files/
│   ├── coco.names
│   ├── ssd_mobilenet.pbtxt
│   └── frozen_inference_graph.pb
│
└── README.md
```

---

## 🚀 Future Improvements

* Add water dispensing module
* Improve pet classification accuracy
* Add feeding history and analytics on web app
* Implement emergency food level alerts

---

## 👥 Team

Developed as an academic / personal IoT project focused on embedded systems, robotics, and intelligent automation.

---

## 📜 License

This project is released for educational and research purposes.
