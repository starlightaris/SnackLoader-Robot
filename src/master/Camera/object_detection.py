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

# Firebase reference for detection status
detRef = db.reference("detectionStatus")

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

# --------------------- SEND TO FIREBASE ---------------------
def send_detection_to_firebase(object_name, confidence):
    timestamp = int(time.time())  # UNIX timestamp

    # Convert numpy float32 → Python float
    safe_confidence = float(round(float(confidence) * 100, 2))

    detRef.child(object_name).set({
        "detected": True,
        "confidence": safe_confidence,
        "timestamp": timestamp
    })

    print(f"Sent to Firebase → {object_name}: {safe_confidence}% at {timestamp}")

# --------------------- OBJECT DETECTION ---------------------
def getObjects(img, thres, nms, draw=True, objects=[]):
    classIds, confs, bbox = net.detect(img, confThreshold=thres, nmsThreshold=nms)
    objectInfo = []

    if len(objects) == 0:
        objects = classNames

    if len(classIds) != 0:
        for classId, confidence, box in zip(classIds.flatten(), confs.flatten(), bbox):
            className = classNames[classId - 1]

            if className in objects:
                objectInfo.append([box, className, confidence])

                if draw:
                    cv2.rectangle(img, box, color=(0, 255, 0), thickness=2)
                    cv2.putText(img, className.upper(), (box[0] + 10, box[1] + 30),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)
                    cv2.putText(img, str(round(float(confidence) * 100, 2)) + '%',
                                (box[0] + 200, box[1] + 30),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)

                    # Center point
                    center_x = box[0] + box[2] // 2
                    center_y = box[1] + box[3] // 2
                    cv2.circle(img, (center_x, center_y), 5, (0, 255, 0), -1)

                # Send to Firebase
                send_detection_to_firebase(className, confidence)

    return img, objectInfo

# --------------------- MAIN PROGRAM ---------------------
if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)

    print("Camera started. Press 'Q' to quit.")

    while True:
        success, img = cap.read()
        if not success:
            print("Failed to read from camera.")
            break

        result, objectInfo = getObjects(img, 0.45, 0.2, objects=['cat', 'dog'])

        cv2.imshow("Output", img)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
