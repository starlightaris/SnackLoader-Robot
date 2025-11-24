import cv2
import serial
import time
import threading
from datetime import datetime
import schedule
import json

# Load class names
classNames = []
classFile = "/home/eutech/Desktop/SnackLoader-Robot/Object_Detection_Files/coco.names"
with open(classFile, "rt") as f:
    classNames = f.read().rstrip("\n").split("\n")

# Load model config and weights
configPath = "/home/eutech/Desktop/SnackLoader-Robot/Object_Detection_Files/ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt"
weightsPath = "/home/eutech/Desktop/SnackLoader-Robot/Object_Detection_Files/frozen_inference_graph.pb"

# Initialize detection model
net = cv2.dnn_DetectionModel(weightsPath, configPath)
net.setInputSize(320, 320)
net.setInputScale(1.0 / 127.5)
net.setInputMean((127.5, 127.5, 127.5))
net.setInputSwapRB(True)

# Initialize serial connections to Arduinos
try:
    arduino_dog = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
    time.sleep(2)
    print("Connected to Dog Feeder (Arduino 1)")
except Exception as e:
    print(f"Failed to connect to Dog Feeder: {e}")
    arduino_dog = None

try:
    arduino_cat = serial.Serial('/dev/ttyACM1', 9600, timeout=1)
    time.sleep(2)
    print("Connected to Cat Feeder (Arduino 2)")
except Exception as e:
    print(f"Failed to connect to Cat Feeder: {e}")
    arduino_cat = None

# Configuration from Web App (you'll get these from Firebase)
MAX_WEIGHTS = {
    'dog': 200.0,  # grams - from web app
    'cat': 100.0   # grams - from web app
}

FEEDING_SCHEDULE = {
    'dog': ['08:00', '18:00'],  # from web app
    'cat': ['07:00', '19:00']   # from web app
}

# Global variables
current_pet_detected = None
last_pet_detection_time = 0
pet_cooldown = 10  # seconds

def send_to_arduino(arduino, command):
    """Send command to specific Arduino"""
    try:
        if arduino:
            arduino.write(f"{command}\n".encode())
            print(f"Sent to Arduino: {command}")
    except Exception as e:
        print(f"Error sending to Arduino: {e}")

def set_max_weights():
    """Set max weights on both Arduinos from web app config"""
    send_to_arduino(arduino_dog, f"MAX_WEIGHT:{MAX_WEIGHTS['dog']}")
    send_to_arduino(arduino_cat, f"MAX_WEIGHT:{MAX_WEIGHTS['cat']}")

def scheduled_dispensing(pet_type):
    """Called by schedule to dispense food"""
    print(f"Scheduled dispensing for {pet_type}")
    if pet_type == 'dog' and arduino_dog:
        send_to_arduino(arduino_dog, "DISPENSE")
    elif pet_type == 'cat' and arduino_cat:
        send_to_arduino(arduino_cat, "DISPENSE")

def setup_schedule():
    """Setup feeding schedule from web app config"""
    for time_str in FEEDING_SCHEDULE['dog']:
        schedule.every().day.at(time_str).do(scheduled_dispensing, 'dog')
        print(f"Scheduled dog feeding at {time_str}")
    
    for time_str in FEEDING_SCHEDULE['cat']:
        schedule.every().day.at(time_str).do(scheduled_dispensing, 'cat')
        print(f"Scheduled cat feeding at {time_str}")

def handle_pet_detection(pet_type):
    """Handle pet detection logic"""
    global current_pet_detected, last_pet_detection_time
    
    current_time = time.time()
    
    # Cooldown check
    if current_time - last_pet_detection_time < pet_cooldown:
        return
    
    # If different pet detected, close the other pet's bowl
    if current_pet_detected and current_pet_detected != pet_type:
        print(f"Different pet detected! Closing {current_pet_detected} bowl")
        if current_pet_detected == 'dog' and arduino_dog:
            send_to_arduino(arduino_dog, "CLOSE_BOWL")
        elif current_pet_detected == 'cat' and arduino_cat:
            send_to_arduino(arduino_cat, "CLOSE_BOWL")
    
    # Open bowl for detected pet
    print(f"{pet_type.capitalize()} detected - opening bowl")
    if pet_type == 'dog' and arduino_dog:
        send_to_arduino(arduino_dog, "OPEN_BOWL")
    elif pet_type == 'cat' and arduino_cat:
        send_to_arduino(arduino_cat, "OPEN_BOWL")
    
    current_pet_detected = pet_type
    last_pet_detection_time = current_time

def getObjects(img, thres, nms, draw=True, objects=[]):
    classIds, confs, bbox = net.detect(img, confThreshold=thres, nmsThreshold=nms)
    objectInfo = []
    if len(objects) == 0: objects = classNames

    if len(classIds) != 0:
        for classId, confidence, box in zip(classIds.flatten(), confs.flatten(), bbox):
            className = classNames[classId - 1]
            if className in objects:
                objectInfo.append([box, className])

                if draw:
                    cv2.rectangle(img, box, color=(0, 255, 0), thickness=2)
                    cv2.putText(img, className.upper(), (box[0]+10, box[1]+30),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(img, str(round(confidence * 100, 2)) + '%', (box[0]+200, box[1]+30),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)

                    center_x = box[0] + box[2] // 2
                    center_y = box[1] + box[3] // 2
                    cv2.circle(img, (center_x, center_y), radius=5, color=(0, 255, 0), thickness=-1)

    return img, objectInfo

def schedule_runner():
    """Run scheduled tasks in background"""
    while True:
        schedule.run_pending()
        time.sleep(1)

# Main program
if __name__ == "__main__":
    # Setup initial configuration
    set_max_weights()
    setup_schedule()
    
    # Start schedule runner thread
    schedule_thread = threading.Thread(target=schedule_runner)
    schedule_thread.daemon = True
    schedule_thread.start()
    
    # Video Capture
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video feed size: {frame_width}x{frame_height}")
    
    # Variables for detection tracking
    last_dog_detection = 0
    last_cat_detection = 0

    while True:
        success, img = cap.read()
        if not success:
            print("Failed to read from camera.")
            break

        # Detect objects
        result, objectInfo = getObjects(img, 0.45, 0.2, objects=['dog', 'cat'])

        # Find closest object (biggest bounding box)
        biggest_box = None
        max_area = 0
        detected_pet = None

        for box, className in objectInfo:
            area = box[2] * box[3]
            if area > max_area:
                max_area = area
                biggest_box = box
                detected_pet = className.lower()  # 'dog' or 'cat'

        # Handle pet detection
        if detected_pet:
            handle_pet_detection(detected_pet)
            
            # Highlight the closest object
            if biggest_box:
                x, y, w, h = biggest_box
                color = (255, 0, 0) if detected_pet == 'dog' else (0, 0, 255)
                cv2.rectangle(img, (x, y), (x+w, y+h), color, 3)
                cv2.putText(img, f"CLOSEST {detected_pet.upper()}", (x, y-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Display status on screen
        status_text = f"Current: {current_pet_detected}" if current_pet_detected else "Monitoring..."
        cv2.putText(img, f"Status: {status_text}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.putText(img, f"Objects: {len(objectInfo)}", (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Display next feeding times
        next_dog = schedule.next_run() if FEEDING_SCHEDULE['dog'] else "No schedule"
        cv2.putText(img, f"Next Dog: {next_dog}", (10, 90), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.putText(img, f"Next Cat: {next_dog}", (10, 110), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        cv2.imshow("Multi-Pet Feeder", img)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('d'):  # Manual dog feed
            scheduled_dispensing('dog')
        elif key == ord('c'):  # Manual cat feed
            scheduled_dispensing('cat')
        elif key == ord('x'):  # Close all
            send_to_arduino(arduino_dog, "CLOSE_ALL")
            send_to_arduino(arduino_cat, "CLOSE_ALL")

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    if arduino_dog:
        arduino_dog.close()
    if arduino_cat:
        arduino_cat.close()