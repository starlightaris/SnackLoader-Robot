import serial
import time
import threading
import firebase_admin
from firebase_admin import credentials, db

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------
SERVICE_ACCOUNT = "/home/eutech/serviceAccountKey.json"
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"

PORT = "/dev/ttyUSB2"   # << CHANGE THIS TO YOUR PORT
BAUD = 9600

POLL_INTERVAL = 0.2

# ---------------------------------------------------------
# INIT
# ---------------------------------------------------------
cred = credentials.Certificate(SERVICE_ACCOUNT)
firebase_admin.initialize_app(cred, {"databaseURL": RTDB_URL})

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)

print("RTDB DISPENSER CONTROLLER STARTED")

# ---------------------------------------------------------
# STATE
# ---------------------------------------------------------
last_run_state = False
is_dispensing = False
last_weight = 0.0


# ---------------------------------------------------------
# FIREBASE HELPERS
# ---------------------------------------------------------
def set_status(status: str):
    """Update status node so your ManualFeed.jsx displays it."""
    db.reference("dispenser/cat").update({"status": status})


def stop_run_flag():
    """Reset run flag after completion."""
    db.reference("dispenser/cat").update({"run": False})


def update_final_weight(w):
    """Store final weight after feeding completes."""
    db.reference("petfeeder/cat/bowlWeight").update({
        "weight": w,
        "unit": "g",
        "timestamp": int(time.time())
    })


# ---------------------------------------------------------
# SERIAL LISTENER
# ---------------------------------------------------------
def serial_listener():
    global last_weight, is_dispensing

    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue

        print("[ARDUINO]", line)

        # LIVE weight updates
        if line.startswith("LIVE"):
            try:
                last_weight = float(line.split()[1])
            except:
                pass

        # FINAL weight after done
        if line.startswith("WEIGHT"):
            try:
                final_w = float(line.split()[1])
                update_final_weight(final_w)
            except:
                pass

        # DISPENSER OPEN
        if line == "OPEN_DISP":
            set_status("dispensing")

        # COMPLETED
        if line == "DONE":
            set_status("completed")
            stop_run_flag()
            is_dispensing = False

        # TIMEOUT STOP FROM ARDUINO
        if line == "TIMEOUT_DISPENSE":
            set_status("aborted_timeout")
            stop_run_flag()
            is_dispensing = False


# ---------------------------------------------------------
# POLL RTDB AND TRIGGER DISPENSE
# ---------------------------------------------------------
def rtdb_loop():
    global last_run_state, is_dispensing

    while True:
        node = db.reference("dispenser/cat").get() or {}

        run = bool(node.get("run", False))
        amount = float(node.get("amount", 0))

        # Frontend pressed FEED
        if run and not last_run_state:
            print(f"FEED REQUEST RECEIVED: {amount}g")

            # Write status for UI
            set_status("starting")

            # Send command to Arduino
            cmd = f"DISPENSE {amount}\n"
            ser.write(cmd.encode())
            is_dispensing = True

        last_run_state = run
        time.sleep(POLL_INTERVAL)


# ---------------------------------------------------------
# START THREADS
# ---------------------------------------------------------
threading.Thread(target=serial_listener, daemon=True).start()
threading.Thread(target=rtdb_loop, daemon=True).start()

# ---------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------
while True:
    time.sleep(1)
