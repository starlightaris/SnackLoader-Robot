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

print("RTDB CAT DISPENSER STARTED (NO ARDUINO CHANGES REQ)")

# ----------------- STATE -----------------
last_run_state = False
is_dispensing = False
lid_open = False

fsm_state = "IDLE"           
start_detect_ts = 0          
timeout_ts = 0               
last_owner_seen_ts = 0       

# Dispenser Watchdog
dispense_start_ts = 0
DISPENSE_TIMEOUT = 10        

# ----------------- FIREBASE REFERENCES -----------------
dispenser_cat_ref = db.reference("dispenser/cat")
petfeeder_cat_ref = db.reference("petfeeder/cat/bowlWeight")
det_ref = db.reference("detectionStatus")

# ----------------- HELPERS -----------------
def send_serial(cmd: str):
    if ser and ser.is_open:
        ser.write((cmd + "\n").encode())
        print("[SEND]", cmd)

def set_status(status: str):
    dispenser_cat_ref.update({"status": status})

def stop_run_flag():
    dispenser_cat_ref.update({"run": False})

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
                    petfeeder_cat_ref.update({"weight": float(line.split()[1]), "timestamp": int(time.time())})

                # If Arduino finishes normally
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
    global fsm_state, start_detect_ts, timeout_ts, last_owner_seen_ts, dispense_start_ts

    while True:
        det = det_ref.get() or {}
        cat_detected = bool(det.get("cat", {}).get("detected", False))
        dog_detected = bool(det.get("dog", {}).get("detected", False))
        now = time.time()

        if cat_detected:
            last_owner_seen_ts = now

        # 1. DISPENSER WATCHDOG (Handles timeout without Arduino knowing)
        if is_dispensing:
            if (now - dispense_start_ts) > DISPENSE_TIMEOUT:
                print("!!! WATCHDOG: Timeout reached. Marking as Empty/Stuck.")
                is_dispensing = False # Stop waiting for 'DONE'
                set_status("OUT_OF_STOCK")
                stop_run_flag()
                # Close the lid even though dispensing "failed"
                if lid_open:
                    send_serial("CLOSE_LID")
                    lid_open = False
                    fsm_state = "IDLE"

        # 2. SMART OVERRIDE (Intruder)
        if dog_detected and lid_open and not is_dispensing:
            if (now - last_owner_seen_ts) > 5:
                time.sleep(2) 
                send_serial("CLOSE_LID")
                lid_open = False
                fsm_state = "IDLE"

        # 3. CAT FSM
        if fsm_state == "IDLE" and cat_detected:
            fsm_state = "CONFIRMING"
            start_detect_ts = now
        elif fsm_state == "CONFIRMING":
            if not cat_detected: fsm_state = "IDLE"
            elif (now - start_detect_ts) >= 5:
                send_serial("OPEN_LID")
                lid_open = True
                fsm_state = "OPEN"
                timeout_ts = now + 600
        elif fsm_state == "OPEN":
            if cat_detected: timeout_ts = now + 600
            if now > timeout_ts and not cat_detected:
                send_serial("CLOSE_LID")
                lid_open = False
                fsm_state = "IDLE"

        # 4. MANUAL FEED
        node = dispenser_cat_ref.get() or {}
        run = bool(node.get("run", False))
        if run and not last_run_state:
            set_status("dispensing")
            if not lid_open:
                send_serial("OPEN_LID")
                lid_open = True
                fsm_state = "OPEN"
                timeout_ts = now + 600
                time.sleep(0.6)
            send_serial(f"DISPENSE {node.get('amount', 0)}")
            is_dispensing = True
            dispense_start_ts = now 

        last_run_state = run
        time.sleep(POLL_INTERVAL)

threading.Thread(target=serial_listener, daemon=True).start()
rtdb_loop()