# dispenser_controller.py
import serial
import time
import threading
import firebase_admin
from firebase_admin import credentials, db

# ----------------- CONFIG -----------------
SERVICE_ACCOUNT = "/home/eutech/serviceAccountKey.json"  # your file
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"

PORT = "/dev/ttyUSB0"   # change to your serial port
BAUD = 9600

POLL_INTERVAL = 0.2  # seconds

# Lid close timeout after dispensing (seconds)
LID_IDLE_TIMEOUT = 20.0

# ----------------- INIT FIREBASE -----------------
cred = credentials.Certificate(SERVICE_ACCOUNT)
firebase_admin.initialize_app(cred, {"databaseURL": RTDB_URL})

# ----------------- SERIAL -----------------
try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
except Exception as e:
    print("Serial open error:", e)
    ser = None

print("RTDB DISPENSER + LID CONTROLLER STARTED")

# ----------------- STATE -----------------
last_run_state = False
is_dispensing = False
last_weight = 0.0

lid_open = False
last_cat_detected = False
last_dog_detected = False
# timestamp of last cat detection (epoch seconds)
last_cat_ts = 0
# whether we are waiting after a dispense to auto-close lid
post_dispense_waiting = False
post_dispense_wait_start = 10

# ----------------- FIREBASE REFERENCES -----------------
dispenser_cat_ref = db.reference("dispenser/cat")
petfeeder_cat_ref = db.reference("petfeeder/cat/bowlWeight")
det_ref = db.reference("detectionStatus")

# ----------------- HELPERS -----------------
def send_serial(cmd: str):
    """Send serial command to Arduino."""
    if ser and ser.is_open:
        ser.write((cmd + "\n").encode())
        print("[SEND]", cmd)
    else:
        print("[SEND-FAILED]", cmd)

def set_status(status: str):
    dispenser_cat_ref.update({"status": status})

def stop_run_flag():
    dispenser_cat_ref.update({"run": False})

def update_final_weight(w):
    petfeeder_cat_ref.update({
        "weight": w,
        "unit": "g",
        "timestamp": int(time.time())
    })

# ----------------- SERIAL LISTENER -----------------
def serial_listener():
    global is_dispensing, post_dispense_waiting, post_dispense_wait_start
    while True:
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode(errors="ignore").strip()
            except:
                continue
            if not line:
                continue
            print("[ARDUINO]", line)

            # Live weight updates
            if line.startswith("LIVE"):
                try:
                    live_weight = float(line.split()[1])
                    # update last weight in RTDB
                    petfeeder_cat_ref.update({
                        "weight": live_weight,
                        "unit": "g",
                        "timestamp": int(time.time())
                    })
                except Exception as e:
                    print("LIVE parse error:", e)

            # Final stable weight
            if line.startswith("WEIGHT"):
                try:
                    final_w = float(line.split()[1])
                    update_final_weight(final_w)
                except:
                    pass

            # OPEN/CLOSE events from Arduino
            if line == "OPEN_LID" or line == "LID_OPENED":
                print("LID opened (arduino reported).")
            if line == "CLOSE_LID" or line == "LID_CLOSED":
                print("LID closed (arduino reported).")

            # When dispensing completes
            if line == "DONE":
                print("Dispense DONE: starting post-dispense waiting")
                # start waiting countdown to auto-close lid
                post_dispense_waiting = True
                post_dispense_wait_start = time.time()
                is_dispensing = False
                set_status("completed")
                stop_run_flag()

        time.sleep(0.01)

# ----------------- MAIN RTDB POLL LOOP -----------------
def rtdb_loop():
    global last_run_state, is_dispensing, last_cat_detected, last_dog_detected
    global last_cat_ts, lid_open, post_dispense_waiting, post_dispense_wait_start

    while True:
        # read detection states
        det = det_ref.get() or {}
        cat_node = det.get("cat", {}) or {}
        dog_node = det.get("dog", {}) or {}

        cat_detected = bool(cat_node.get("detected", False))
        dog_detected = bool(dog_node.get("detected", False))

        # update timestamps if detected
        if cat_detected:
            last_cat_ts = int(time.time())

        # --- Lid logic based on detections (immediate rules) ---
        # If dog detected OR both present -> close lid immediately
        if dog_detected and lid_open and is_dispensing == false:
            print("Dog detected -> immediate lid close")
            send_serial("CLOSE_LID")
            lid_open = False
            # cancel any post-dispense wait
            post_dispense_waiting = False

        elif cat_detected and dog_detected:
            # both present -> close immediately (safety)
            if lid_open:
                print("Both detected -> immediate lid close")
                send_serial("CLOSE_LID")
                lid_open = False
                post_dispense_waiting = False

        elif cat_detected and not dog_detected:
            # cat-only visible -> open lid immediately if closed
            if not lid_open:
                print("Cat detected -> open lid")
                send_serial("OPEN_LID")
                lid_open = True
                # don't start/stop post dispense here; if dispensing happening, lid stays open.

        # --- Poll for frontend-run feed request ---
        node = dispenser_cat_ref.get() or {}
        run = bool(node.get("run", False))
        amount = float(node.get("amount", 0) or 0)

        # Frontend pressed FEED
        if run and not last_run_state:
            print(f"FEED REQUEST RECEIVED: {amount}g")
            set_status("starting")
            # Ensure lid is open BEFORE dispensing
            if not lid_open:
                print("Opening lid before dispense")
                send_serial("OPEN_LID")
                lid_open = True
                # give Arduino small time to move lid before dispensing
                time.sleep(0.6)
            # send dispense command
            cmd = f"DISPENSE {amount}"
            send_serial(cmd)
            is_dispensing = True

        last_run_state = run

        # --- Post-dispense waiting logic ---
        if post_dispense_waiting:
            elapsed = time.time() - post_dispense_wait_start
            # If dog detected during wait -> close immediately
            if dog_detected:
                print("Dog detected during post-dispense -> immediate close")
                send_serial("CLOSE_LID")
                lid_open = False
                post_dispense_waiting = False

            # If both detected -> close immediately
            elif cat_detected and dog_detected:
                print("Both detected during post-dispense -> close")
                send_serial("CLOSE_LID")
                lid_open = False
                post_dispense_waiting = False

            # If cat seen recently (within timeout), keep waiting and reset timer
            elif (time.time() - last_cat_ts) < LID_IDLE_TIMEOUT:
                # cat present recently — keep lid open, restart timer (we implement by sliding window)
                # Reset wait start so we get a full LID_IDLE_TIMEOUT after last detection
                post_dispense_wait_start = time.time()
            else:
                # no cat detected within timeout -> close lid
                if lid_open:
                    print("No cat detected for timeout -> closing lid")
                    send_serial("CLOSE_LID")
                    lid_open = False
                post_dispense_waiting = False

        # --- Safety: if both not detected and lid is open and not in post-dispense wait,
        # optionally close after some idle (optional) — we will not auto-close here to avoid
        # interfering with intended open times. Keep conservative.

        time.sleep(POLL_INTERVAL)

# ----------------- START THREADS -----------------
threading.Thread(target=serial_listener, daemon=True).start()
threading.Thread(target=rtdb_loop, daemon=True).start()

# ----------------- KEEPALIVE -----------------
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting.")
