import requests
import time
from camera_worker import start_camera, stop_camera

API_URL = "https://snackloader-backend-production.up.railway.app/api/device/commands/camera"

last_state = None

while True:
    try:
        response = requests.get(API_URL).json()
        turnOn = response.get("turnOn", False)

        if turnOn != last_state:
            if turnOn:
                start_camera()
            else:
                stop_camera()

            last_state = turnOn

    except Exception as e:
        print("Error:", e)

    time.sleep(3)
