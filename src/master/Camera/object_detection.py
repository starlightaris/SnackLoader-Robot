# -------------------- Import OpenCV & Firebase --------------------
import cv2
import time
import numpy as np
import firebase_admin
from firebase_admin import credentials, db

# --------------------- FIREBASE SETUP -----------------------------
cred = credentials.Certificate("/home/eutech/serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"
})

detRef = db.reference("detectionStatus")

# Track last detection state (to avoid spamming Firebase)
last_detect = {"cat": False, "dog": False}

# --------------------- LOAD COCO MODEL ----------------------------
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

# ---------------------- FIREBASE HELPERS --------------------------
def send_detected(animal, confidence):
    timestamp = int(time.time())
    conf = float(round(float(confidence) * 100, 2))

    detRef.child(animal).set({
        "confidence": conf,
        "detected": True,
        "timestamp": timestamp
    })

    print(f"✔ {animal.upper()} detected — {conf}%")

def send_not_detected(animal):
    lastSeen = detRef.child(animal).child("timestamp").get()

    detRef.child(animal).set({
        "confidence": 0,
        "detected": False,
        "timestamp": lastSeen or int(time.time())
    })

    print(f"✘ {animal.upper()} not detected")

# ---------------------- DETECTION FUNCTION ------------------------
def getObjects(img, thres, nms, draw=True):
    classIds, confs, bbox = net.detect(img, confThreshold=thres, nmsThreshold=nms)
    detected_now = {"cat": False, "dog": False}

    if len(classIds) != 0:
        for classId, confidence, box in zip(classIds.flatten(), confs.flatten(), bbox):

            className = classNames[classId - 1]

            if className in ["cat", "dog"]:
                detected_now[className] = True

                if draw:
                    # Bounding box
                    cv2.rectangle(img, box, (0, 255, 0), 2)

                    # Label
                    cv2.putText(img, className.upper(), (box[0]+10, box[1]+30),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

                    # Confidence
                    cv2.putText(img, str(round(float(confidence)*100, 2)) + "%",
                                (box[0]+200, box[1]+30),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)

                    # Center point
                    cx = box[0] + box[2]//2
                    cy = box[1] + box[3]//2
                    cv2.circle(img, (cx,cy), 5, (0,255,0), -1)

                # Send detection to Firebase
                send_detected(className, confidence)

    return img, detected_now

# --------------------------- MAIN LOOP ----------------------------
cap = cv2.VideoCapture(0)
cap.set(3, 640)
cap.set(4, 480)

print("🐈🐕 Cat & Dog Detector Started (Press Q to Quit)")

while True:
    success, img = cap.read()
    if not success:
        print("Camera not found!")
        break

    img, detected = getObjects(img, 0.45, 0.2, draw=True)

    # --- Handle NOT detected transitions ---
    for animal in ["cat", "dog"]:
        if detected[animal]:
            last_detect[animal] = True
        else:
            if last_detect[animal] is True:  # only send when state changes
                send_not_detected(animal)
            last_detect[animal] = False

    cv2.imshow("Cat & Dog Detector", img)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
