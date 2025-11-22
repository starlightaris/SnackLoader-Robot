import serial
import time
import firebase_admin
from firebase_admin import credentials, db

# ---------------------
# Firebase Setup
# ---------------------
cred = credentials.Certificate("/home/pi/firebase-service-account.json")
firebase_admin.initialize_app(cred, {
    'databaseURL' : "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"
})

rtdb_ref = db.reference("/petfeeder/cat")

# ---------------------
# Arduino Setup
# ---------------------
arduino = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
time.sleep(2)
print("Connected to Arduino CAT feeder")

# ---------------------
# Read Loop
# ---------------------
while True:
    try:
        line = arduino.readline().decode().strip()

        if line.startswith("WEIGHT:"):
            weight = float(line.split(":")[1])

            print("Cat Weight:", weight)

            # update realtime database
            rtdb_ref.update({
                "bowlWeight": weight,
                "timestamp": time.time()
            })

    except Exception as e:
        print("Error:", e)

    time.sleep(0.05)
