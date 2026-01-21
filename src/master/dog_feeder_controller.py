# dispenser_controller_dog.py
import serial
import time
import threading
import firebase_admin
from firebase_admin import credentials, db

# ----------------- CONFIG -----------------
SERVICE_ACCOUNT = "/home/eutech/serviceAccountKey.json" 
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"

PORT = "/dev/ttyACM0" 
BAUD = 9600

POLL_INTERVAL = 0.2 


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

print("RTDB DOG DISPENSER + LID CONTROLLER STARTED")

# ----------------- STATE -----------------
last_run_state = False
is_dispensing = False
last_weight = 0.0

lid_open = False
last_cat_detected = False
last_dog_detected = False
last_dog_ts = 0

# --- NEW FSM STATE VARIABLES ---
fsm_state = "IDLE"           # IDLE, CONFIRMING, OPEN
start_detect_ts = 0          # Timer for the 5s check
timeout_ts = 0               # Timer for the 10m window
# -------------------------------

# ----------------- FIREBASE REFERENCES -----------------
dispenser_dog_ref = db.reference("dispenser/dog")
petfeeder_dog_ref = db.reference("petfeeder/dog/bowlWeight")
det_ref = db.reference("detectionStatus")

# ----------------- HELPERS -----------------
def send_serial(cmd: str):
    if ser and ser.is_open:
        ser.write((cmd + "\n").encode())
        print("[SEND]", cmd)
    else:
        print("[SEND-FAILED]", cmd)

def set_status(status: str):
    dispenser_dog_ref.update({"status": status})

def stop_run_flag():
    dispenser_dog_ref.update({"run": False})

def update_final_weight(w):
    petfeeder_dog_ref.update({
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

            if line.startswith("LIVE"):
                try:
                    live_weight = float(line.split()[1])
                    petfeeder_dog_ref.update({
                        "weight": live_weight,
                        "unit": "g",
                        "timestamp": int(time.time())
                    })
                except Exception as e:
                    print("LIVE parse error:", e)

            if line.startswith("WEIGHT"):
                try:
                    final_w = float(line.split()[1])
                    update_final_weight(final_w)
                except:
                    pass

            if line == "OPEN_LID" or line == "LID_OPENED":
                print("LID opened (arduino reported).")
            if line == "CLOSE_LID" or line == "LID_CLOSED":
                print("LID closed (arduino reported).")

            if line == "DONE":
                print("Dispense DONE")
                is_dispensing = False
                set_status("completed")
                stop_run_flag()

        time.sleep(0.01)

# ----------------- MAIN RTDB POLL LOOP -----------------
def rtdb_loop():
    global last_run_state, is_dispensing, last_cat_detected, last_dog_detected
    global last_dog_ts, lid_open
    global fsm_state, start_detect_ts, timeout_ts

    while True:
        det = det_ref.get() or {}
        cat_node = det.get("cat", {}) or {}
        dog_node = det.get("dog", {}) or {}

        cat_detected = bool(cat_node.get("detected", False))
        dog_detected = bool(dog_node.get("detected", False))

        now = time.time()

        # --- FSM LID LOGIC ---

        # 1. CAT OVERRIDE: Close in 2 sec if cat detected
        if cat_detected and lid_open and is_dispensing == False:
            print("!!! Cat detected at Dog bowl: Closing in 2 seconds...")
            time.sleep(2) 
            send_serial("CLOSE_LID")
            lid_open = False
            fsm_state = "IDLE"
            # Note: The dog lid logic pauses here, allowing the dog lid to close 
            # before the dog logic can re-evaluate the dog's presence.
            
        # 2. DOG FSM
        elif fsm_state == "IDLE":
            if dog_detected:
                fsm_state = "CONFIRMING"
                start_detect_ts = now
                print("Dog spotted... starting 5s confirmation.")
        
        elif fsm_state == "CONFIRMING":
            if not dog_detected:
                fsm_state = "IDLE"
            elif (now - start_detect_ts) >= 5: # Updated to 5s Delay
                print("Dog confirmed (5s) -> open lid")
                send_serial("OPEN_LID")
                lid_open = True
                fsm_state = "OPEN"
                timeout_ts = now + 600 
        
        elif fsm_state == "OPEN":
            if dog_detected:
                timeout_ts = now + 600
            
            if now > timeout_ts and not dog_detected:
                print("Dog timeout reached -> closing lid")
                send_serial("CLOSE_LID")
                lid_open = False
                fsm_state = "IDLE"

        # --- Poll for frontend-run feed request ---
        node = dispenser_dog_ref.get() or {}
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

# ----------------- START THREADS -----------------
threading.Thread(target=serial_listener, daemon=True).start()
threading.Thread(target=rtdb_loop, daemon=True).start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Exiting.")
    if lid_open:
        send_serial("CLOSE_LID")