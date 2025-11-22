import serial
import firebase_admin
from firebase_admin import credentials, firestore

# -------------------- Firebase Setup -------------------------
cred = credentials.Certificate("/home/eutech/serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()
cat_ref = db.collection("feeder").document("bowlWeights")

# -------------------- Serial Setup (your port) ----------------
cat_port = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)

print("Listening for CAT bowl weight on /dev/ttyUSB0...")

while True:
    try:
        line = cat_port.readline().decode().strip()

        if "CAT" in line:
            weight_val = float(line.split()[0])
            print("Cat Weight:", weight_val, "kg")

            cat_ref.set({
                "catWeight": weight_val
            }, merge=True)

    except Exception as e:
        print("Error:", e)
