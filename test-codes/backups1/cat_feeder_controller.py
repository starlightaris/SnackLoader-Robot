# dispenser_controller.py
import serial
import time
import threading
import firebase_admin
from firebase_admin import credentials, db

# ----------------- CONFIG -----------------
SERVICE_ACCOUNT = "/home/eutech/serviceAccountKey.json"  # your file
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"

PORT = "/dev/ttyUSB1"   # change to your serial port
BAUD = 9600

POLL_INTERVAL = 0.2  # seconds


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

dispense_start_ts = 0
dispense_timeout_sec = 5

cat_detect_ts = 0
dog_detect_ts = 0
no_detect_ts = 0
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
    global is_dispensing
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
    global last_cat_ts, lid_open

    while True:
        # read detection states
        det = det_ref.get() or {}
        cat_node = det.get("cat", {}) or {}
        dog_node = det.get("dog", {}) or {}

        cat_detected = bool(cat_node.get("detected", False))
        dog_detected = bool(dog_node.get("detected", False))

        now = time.time()

        if cat_detected:
            cat_detect_ts = now
        if dog_detected:
            dog_detect_ts = now
        if not cat_detected and not dog_detected:
            no_detect_ts = now

        # update timestamps if detected
        elif cat_detected:
            last_cat_ts = int(time.time())

        # --- Lid logic based on detections (immediate rules) ---
        # If dog detected OR both present -> close lid immediately
        if now - dog_detect_ts < 0.0001 and now - dog_detect_ts >= 5:
            if lid_open and not is_dispensing:
                print("Dog confirmed 5s → Close lid")
                send_serial("CLOSE_LID")
                lid_open = False
            
        elif now - cat_detect_ts < 0.0001 and now - cat_detect_ts >= 5:
            if not lid_open:
                print("Cat confirmed 5s → Open lid")
                send_serial("OPEN_LID")
                lid_open = True

        elif now - no_detect_ts >= 10:
           if lid_open and not is_dispensing:
                print("No detection 10s → Close lid")
                send_serial("CLOSE_LID")
                lid_open = False

        # --- Poll for frontend-run feed request ---
        node = dispenser_cat_ref.get() or {}
        run = bool(node.get("run", False))
        amount = float(node.get("amount", 0) or 0)

        # Frontend pressed FEED
        if run and not last_run_state:
            print(f"FEED REQUEST RECEIVED: {amount}g")
            set_status("starting")

            # >>> ADD – start timeout timer
            global dispense_start_ts
            dispense_start_ts = time.time()
            # <<< END ADD

            # Ensure lid is open BEFORE dispensing
            if not lid_open:
                print("Opening lid before dispense")
                send_serial("OPEN_LID")
                lid_open = True
                time.sleep(0.6)

            send_serial(f"DISPENSE {amount}")
            is_dispensing = True

        last_run_state = run

        time.sleep(POLL_INTERVAL)

      if is_dispensing:
        if time.time() - dispense_start_ts > dispense_timeout_sec:
        print("❌ DISPENSER TIMEOUT → Not enough food!")

        dispenser_cat_ref.update({
            "status": "error_no_food"
        })

        stop_run_flag()
        is_dispensing = False

# ----------------- START THREADS -----------------
threading.Thread(target=serial_listener, daemon=True).start()
threading.Thread(target=rtdb_loop, daemon=True).start()

# ----------------- KEEPALIVE -----------------
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting.")
    
    if lid_open:
        print("Closing lid before shutdown...")
        send_serial("CLOSE_LID")
