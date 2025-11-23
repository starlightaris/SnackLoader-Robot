import serial, time, threading
import firebase_admin
from firebase_admin import credentials, db

# ---------------- FIREBASE SETUP ----------------
SERVICE = "/home/eutech/serviceAccountKey.json"
URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app"

cred = credentials.Certificate(SERVICE)
firebase_admin.initialize_app(cred, {"databaseURL": URL})

# ---------------- SERIAL SETUP -------------------
PORT = "/dev/ttyUSB0"   # update: /dev/ttyACM0 if needed
BAUD = 9600
ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

# ---------------- FUNCTIONS -----------------------
def upload_weight(weight):
    db.reference("petfeeder/cat/bowlWeight").update({
        "weight": float(weight),
        "unit": "g",
        "timestamp": int(time.time())
    })

def listen_serial():
    while True:
        try:
            line = ser.readline().decode().strip()
            if not line:
                continue

            if line.startswith("LIVE"):
                w = float(line.split()[1])
                upload_weight(w)

            if line.startswith("WEIGHT"):
                w = float(line.split()[1])
                upload_weight(w)

            if line == "DONE":
                db.reference("dispenser/cat").update({
                    "status": "completed",
                    "run": False
                })

        except Exception as e:
            print("Serial Error:", e)

def listen_rtdb():
    last_run = False
    while True:
        node = db.reference("dispenser/cat").get() or {}
        run = node.get("run", False)
        amount = node.get("amount", 0)

        if run and not last_run:
            ser.write(f"DISPENSE {amount}\n".encode())
            db.reference("dispenser/cat").update({"status": "feeding"})

        last_run = run
        time.sleep(0.2)

# ---------------- START THREADS ------------------
threading.Thread(target=listen_serial, daemon=True).start()
threading.Thread(target=listen_rtdb, daemon=True).start()

print("Feeder Controller Running...")
while True:
    time.sleep(1)
