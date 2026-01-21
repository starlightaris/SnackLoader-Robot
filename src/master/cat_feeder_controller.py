# dispenser_controller_cat.py
import serial
import time
import threading
import firebase_admin
from firebase_admin import credentials, db

# ----------------- CONFIG -----------------
SERVICE_ACCOUNT = "/home/eutech/serviceAccountKey.json"
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"

PORT = "/dev/ttyUSB0" 
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

print("RTDB CAT DISPENSER + LID CONTROLLER STARTED")

# ----------------- STATE -----------------
last_run_state = False
is_dispensing = False
lid_open = False

# FSM & Timing State
fsm_state = "IDLE"           # IDLE, CONFIRMING, OPEN
start_detect_ts = 0          # Timer for the 5s confirmation
timeout_ts = 0               # Timer for the 10m feeding window
last_owner_seen_ts = 0       # Tracks exactly when the CAT was last seen

# ----------------- FIREBASE REFERENCES -----------------
dispenser_cat_ref = db.reference("dispenser/cat")
petfeeder_cat_ref = db.reference("petfeeder/cat/bowlWeight")
det_ref = db.reference("detectionStatus")

# ----------------- HELPERS -----------------
def send_serial(cmd: str):
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
                if not line: continue
                print("[ARDUINO]", line)

                if line.startswith("LIVE"):
                    try:
                        live_weight = float(line.split()[1])
                        petfeeder_cat_ref.update({
                            "weight": live_weight,
                            "unit": "g",
                            "timestamp": int(time.time())
                        })
                    except: pass

                if line.startswith("WEIGHT"):
                    try:
                        final_w = float(line.split()[1])
                        update_final_weight(final_w)
                    except: pass

                if line == "DONE":
                    is_dispensing = False
                    set_status("completed")
                    stop_run_flag()
            except:
                continue
        time.sleep(0.01)

# ----------------- MAIN RTDB POLL LOOP -----------------
def rtdb_loop():
    global last_run_state, is_dispensing, lid_open
    global fsm_state, start_detect_ts, timeout_ts, last_owner_seen_ts

    while True:
        # read detection states
        det = det_ref.get() or {}
        cat_node = det.get("cat", {}) or {}
        dog_node = det.get("dog", {}) or {}

        cat_detected = bool(cat_node.get("detected", False))
        dog_detected = bool(dog_node.get("detected", False))

        now = time.time()

        # Update Cat presence timestamp
        if cat_detected:
            last_owner_seen_ts = now

        # --- SMART OVERRIDE LOGIC ---
        # If Dog is here and Lid is open, but Cat hasn't been seen for 5 seconds
        if dog_detected and lid_open and not is_dispensing:
            if (now - last_owner_seen_ts) > 5:
                print("!!! Dog detected AND Cat is missing > 5s. Closing in 2s...")
                time.sleep(2) 
                send_serial("CLOSE_LID")
                lid_open = False
                fsm_state = "IDLE"

        # --- CAT FINITE STATE MACHINE ---
        if fsm_state == "IDLE":
            if cat_detected:
                fsm_state = "CONFIRMING"
                start_detect_ts = now
                print("Cat spotted... checking 5s confirmation.")

        elif fsm_state == "CONFIRMING":
            if not cat_detected:
                fsm_state = "IDLE"
            elif (now - start_detect_ts) >= 5:
                print("Cat confirmed (5s) -> open lid")
                send_serial("OPEN_LID")
                lid_open = True
                fsm_state = "OPEN"
                timeout_ts = now + 600 # 10 minute window

        elif fsm_state == "OPEN":
            # Extend 10m timer if cat is seen
            if cat_detected:
                timeout_ts = now + 600
            
            # Auto-close if timeout reached and cat is gone
            if now > timeout_ts and not cat_detected:
                print("Feeding window expired. Closing lid.")
                send_serial("CLOSE_LID")
                lid_open = False
                fsm_state = "IDLE"

        # --- MANUAL FEED REQUEST ---
        node = dispenser_cat_ref.get() or {}
        run = bool(node.get("run", False))
        amount = float(node.get("amount", 0) or 0)

        if run and not last_run_state:
            print(f"FEED REQUEST RECEIVED: {amount}g")
            set_status("starting")
            if not lid_open:
                send_serial("OPEN_LID")
                lid_open = True
                fsm_state = "OPEN"
                timeout_ts = now + 600
                time.sleep(0.6)
            send_serial(f"DISPENSE {amount}")
            is_dispensing = True

        last_run_state = run
        time.sleep(POLL_INTERVAL)

# ----------------- EXECUTION -----------------
threading.Thread(target=serial_listener, daemon=True).start()
try:
    rtdb_loop()
except KeyboardInterrupt:
    print("Exiting.")
    if lid_open:
        send_serial("CLOSE_LID")