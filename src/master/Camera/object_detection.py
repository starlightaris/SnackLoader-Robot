# Import OpenCV
import cv2
import time
import numpy as np
import firebase_admin
from firebase_admin import credentials, db

# --------------------- FIREBASE SETUP ---------------------
cred = credentials.Certificate("/home/eutech/serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"
})

# Firebase reference
detRef = db.reference("detectionStatus")

# Track last detection state
last_detect = {"cat": False, "dog": False}

# --------------------- LOAD COCO + MODEL ---------------------
classNames = []
classFile = "/home/eutech/Desktop/SnackLoader-Robot/Object_Detection_Files/coco.names"
with open(classFile, "rt") as f:
    classNames = f.read().rstrip("\n").split("\n")

configPath = "/home/eutech/Desktop/SnackLoader-Robot/Object_Detection_Files/ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt"
weightsPath = "/home/eutech/Desktop/SnackLoader-Robot/Object_Detection_Files/frozen_inference_graph.pb"

net = cv2.dnn_DetectionModel(weightsPath, configPath)
net.setInputSize(320, 320)
net.setInputScale(1.0 / 127.5)
net.setInputMean((127.5, 127.5, 127.5))
net.setInputSwapRB(True)

# --------------------- TRUE WHEN DETECTED ---------------------
def send_detected(object_name, confidence):
    timestamp = int(time.time())
    conf = float(round(float(confidence) * 100, 2))

    detRef.child(object_name).set({
        "confidence": conf,
        "detected": True,
        "timestamp": timestamp
    })

    print(f"{object_name} detected — {conf}%")

# --------------------- FALSE WHEN NOT DETECTED ---------------------
def send_not_detected(object_name):
    # Keep last timestamp
    lastSeen = detRef.child(object_name).child("timestamp").get()

    detRef.child(object_name).set({
        "confidence": 0,
        "detected": False,
        "timestamp": lastSeen
    })

    print(f"{object_name} NOT detected — set to false")

# --------------------- OBJECT DETECTION ---------------------
def getObjects(img, thres, nms, draw=True):
    classIds, confs, bbox = net.detect(img, confThreshold=thres, nmsThreshold=nms)
    detected_now = {"cat": False, "dog": False}

    if len(classIds) != 0:
        for classId, confidence, box in zip(classIds.flatten(), confs.flatten(), bbox):
            className = classNames[classId - 1]

            if className in ["cat", "dog"]:
                detected_now[className] = True

                # ---------------- DRAWING (GREEN BOX + TEXT + CENTER POINT) ----------------
                if draw:
                    # Rectangle box
                    cv2.rectangle(img, box, color=(0, 255, 0), thickness=2)

                    # Label name
                    cv2.putText(img, className.upper(), (box[0] + 10, box[1] + 30),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)

                    # Confidence text
                    cv2.putText(img, str(round(float(confidence) * 100, 2)) + '%',
                                (box[0] + 200, box[1] + 30),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)

                    # Center point
                    cx = box[0] + box[2] // 2
                    cy = box[1] + box[3] // 2
                    cv2.circle(img, (cx, cy), 5, (0, 255, 0), -1)

                # ---------------- SEND TO FIREBASE ----------------
                send_detected(className, confidence)

    return img, detected_now

# --------------------- MAIN LOOP ---------------------
cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

print("Camera started. Press Q to quit.")

while True:
    success, img = cap.read()
    if not success:
        print("Camera error.")
        break

    img, detected = getObjects(img, 0.45, 0.2, draw=True)

    # Send false when not detected
    for animal in ["cat", "dog"]:
        if detected[animal] is False:
            if last_detect[animal] is True:  # only send when detection stops
                send_not_detected(animal)
            last_detect[animal] = False
        else:
            last_detect[animal] = True

    cv2.imshow("Output", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
