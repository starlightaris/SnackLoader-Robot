import cv2
import time

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

# Function to detect objects and mark centers
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
                    # Draw rectangle
                    cv2.rectangle(img, box, color=(0, 255, 0), thickness=2)
                    # Draw class name
                    cv2.putText(img, className.upper(), (box[0]+10, box[1]+30),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)
                    # Draw confidence
                    cv2.putText(img, str(round(confidence * 100, 2)) + '%', (box[0]+200, box[1]+30),
                                cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0), 2)

                    # Compute center of the bounding box
                    center_x = box[0] + box[2] // 2
                    center_y = box[1] + box[3] // 2

                    # Draw small circle at the center
                    cv2.circle(img, (center_x, center_y), radius=5, color=(0, 255, 0), thickness=-1)

    return img, objectInfo

# Main program
if __name__ == "__main__":
    # Video Capture
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)

    # Optional: print frame size
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Video feed size: {frame_width}x{frame_height}")
    
    # Variables for condition tracking
    condition_met = False
    last_trigger_time = 0
    trigger_cooldown = 3  # seconds

    while True:
        success, img = cap.read()
        if not success:
            print("Failed to read from camera.")
            break

        # Detect objects and mark centers of their bounding boxes
        result, objectInfo = getObjects(img, 0.45, 0.2, objects=['bottle']) #CHANGE OBJECT HERE

        # Find closest object (biggest bounding box)
        biggest_box = None
        max_area = 0
        object_detected = False

        for box, className in objectInfo:
            area = box[2] * box[3]  # width * height
            if area > max_area:
                max_area = area
                biggest_box = box
                object_detected = True

        # Optional: You can also draw the biggest box differently to highlight it
        if biggest_box is not None:
            # Highlight the closest object with a different color
            x, y, w, h = biggest_box
            cv2.rectangle(img, (x, y), (x+w, y+h), (255, 0, 0), 3)  # Blue box for closest
            cv2.putText(img, "CLOSEST", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
    
        current_time = time.time()
        
        if object_detected:
            # Only trigger if cooldown has passed
            if current_time - last_trigger_time > trigger_cooldown:
                condition_met = True
                last_trigger_time = current_time
                print(f"Object detected - Area: {max_area}")
                time.sleep(3)
            else:
                condition_met = False  # Still in cooldown
        else:
            condition_met = False
        
        # Display status on screen
        status_text = "CONDITION MET!" if condition_met else "Monitoring..."
        status_color = (0, 255, 0) if condition_met else (255, 255, 255)
        
        cv2.putText(img, f"Status: {status_text}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
        cv2.putText(img, f"Objects detected: {len(objectInfo)}", (10, 60), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.putText(img, f"Largest area: {max_area}", (10, 90), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
        cv2.imshow("Output", img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()