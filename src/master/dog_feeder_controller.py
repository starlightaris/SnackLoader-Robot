# dispenser_controller_dog.py
import serial
import time
import threading
import firebase_admin
from firebase_admin import credentials, db

# ----------------- CONFIG -----------------
SERVICE_ACCOUNT = "/home/eutech/serviceAccountKey.json"
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"

PORT = "/dev/ttyACM0"   # Dog Arduino Port
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

print("RTDB DOG DISPENSER STARTED (NO ARDUINO CHANGES REQ)")

# ----------------- STATE -----------------
last_run_state = False
is_dispensing = False
lid_open = False

fsm_state = "IDLE"           # IDLE, CONFIRMING, OPEN
start_detect_ts = 0          # Timer for 5s check
timeout_ts = 0               # Timer for 10m window
last_owner_seen_ts = 0       # Tracks when DOG was last seen

# Dispenser Watchdog
dispense_start_ts = 0
DISPENSE_TIMEOUT = 10        # 10s timeout window

# ----------------- FIREBASE REFERENCES -----------------
dispenser_dog_ref = db.reference("dispenser/dog")
petfeeder_dog_ref = db.reference("petfeeder/dog/bowlWeight")
det_ref = db.reference("detectionStatus")

# ----------------- HELPERS -----------------
def send_serial(cmd: str):
    if ser and ser.is_open:
        ser.write((cmd + "\n").encode())
        print("[SEND]", cmd)

def set_status(status: str):
    dispenser_dog_ref.update({"status": status})

def stop_run_flag():
    dispenser_dog_ref.update({"run": False})

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
                    petfeeder_dog_ref.update({
                        "weight": float(line.split()[1]), 
                        "timestamp": int(time.time())
                    })

                # Normal completion from Arduino
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

        if dog_detected:
            last_owner_seen_ts = now

        # 1. DISPENSER WATCHDOG (Python-side timeout)
        if is_dispensing:
            if (now - dispense_start_ts) > DISPENSE_TIMEOUT:
                print("!!! WATCHDOG: Timeout. Target weight not met. Container likely empty.")
                is_dispensing = False 
                set_status("OUT_OF_STOCK")
                stop_run_flag()
                # Close lid immediately since owner might leave while stuck
                if lid_open:
                    send_serial("CLOSE_LID")
                    lid_open = False
                    fsm_state = "IDLE"

        # 2. SMART OVERRIDE (Intruder)
        # Close if cat is at dog bowl and dog has been gone > 5s
        if cat_detected and lid_open and not is_dispensing:
            if (now - last_owner_seen_ts) > 5:
                print("!!! Intruder: Cat detected, Dog missing. Closing in 2s...")
                time.sleep(2) 
                send_serial("CLOSE_LID")
                lid_open = False
                fsm_state = "IDLE"

        # 3. DOG FINITE STATE MACHINE
        if fsm_state == "IDLE" and dog_detected:
            fsm_state = "CONFIRMING"
            start_detect_ts = now
            print("Dog spotted... checking 5s confirmation.")

        elif fsm_state == "CONFIRMING":
            if not dog_detected:
                fsm_state = "IDLE"
            elif (now - start_detect_ts) >= 5:
                print("Dog confirmed (5s) -> opening lid")
                send_serial("OPEN_LID")
                lid_open = True
                fsm_state = "OPEN"
                timeout_ts = now + 600 # 10m feeding window

        elif fsm_state == "OPEN":
            if dog_detected:
                timeout_ts = now + 600
            
            if now > timeout_ts and not dog_detected:
                print("Feeding window expired. Closing lid.")
                send_serial("CLOSE_LID")
                lid_open = False
                fsm_state = "IDLE"

        # 4. MANUAL FEED REQUEST
        node = dispenser_dog_ref.get() or {}
        run = bool(node.get("run", False))
        if run and not last_run_state:
            print(f"FEED REQUEST: {node.get('amount', 0)}g")
            set_status("dispensing")
            if not lid_open:
                send_serial("OPEN_LID")
                lid_open = True
                fsm_state = "OPEN"
                timeout_ts = now + 600
                time.sleep(0.6)
            
            send_serial(f"DISPENSE {node.get('amount', 0)}")
            is_dispensing = True
            dispense_start_ts = now # Start the 10s watchdog clock

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