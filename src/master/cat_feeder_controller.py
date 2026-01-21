import serial
import time
import threading
import firebase_admin
from firebase_admin import credentials, db

# --- CONFIG ---
SERVICE_ACCOUNT = "/home/eutech/serviceAccountKey.json"
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"
PORT = "/dev/ttyUSB0" 
BAUD = 9600
POLL_INTERVAL = 0.5  # Slightly slower polling is better for FSM stability

# --- FSM SETTINGS ---
CONFIRMATION_TIME = 3    # Seconds pet must be seen to open
FEEDING_WINDOW = 600     # 10 minutes (in seconds) to stay open

# --- INIT FIREBASE ---
cred = credentials.Certificate(SERVICE_ACCOUNT)
firebase_admin.initialize_app(cred, {"databaseURL": RTDB_URL})

# --- SERIAL ---
try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    print("Serial connected to Arduino.")
except Exception as e:
    print("Serial open error:", e)
    ser = None

# --- FIREBASE REFERENCES ---
dispenser_cat_ref = db.reference("dispenser/cat")
petfeeder_cat_ref = db.reference("petfeeder/cat/bowlWeight")
det_ref = db.reference("detectionStatus")

# --- GLOBAL STATE ---
class CatFSM:
    def __init__(self):
        self.state = "IDLE"           # IDLE, CONFIRMING, OPEN
        self.lid_open = False
        self.is_dispensing = False
        self.last_run_state = False
        
        self.start_detect_ts = 0      # For the 3s check
        self.timeout_ts = 0           # For the 10m check

cat_unit = CatFSM()

# --- HELPERS ---
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

# --- SERIAL LISTENER ---
def serial_listener():
    while True:
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode(errors="ignore").strip()
                if not line: continue
                print("[ARDUINO]", line)

                if line.startswith("LIVE"):
                    try:
                        live_w = float(line.split()[1])
                        petfeeder_cat_ref.update({
                            "weight": live_w,
                            "unit": "g",
                            "timestamp": int(time.time())
                        })
                    except: pass

                if line == "DONE":
                    cat_unit.is_dispensing = False
                    set_status("completed")
                    stop_run_flag()
            except:
                continue
        time.sleep(0.01)

# --- MAIN FSM & RTDB LOOP ---
def rtdb_loop():
    while True:
        now = time.time()
        
        # 1. READ DETECTION STATES
        det = det_ref.get() or {}
        cat_detected = bool(det.get("cat", {}).get("detected", False))
        dog_detected = bool(det.get("dog", {}).get("detected", False))

        # 2. FINITE STATE MACHINE LOGIC
        
        # SAFETY RULE: If dog shows up at cat bowl, override everything and close
        if dog_detected and cat_unit.lid_open:
            print("!!! DOG DETECTED at Cat Bowl - Safety Close")
            send_serial("CLOSE_LID")
            cat_unit.lid_open = False
            cat_unit.state = "IDLE"

        # STATE: IDLE (Waiting for cat)
        elif cat_unit.state == "IDLE":
            if cat_detected:
                cat_unit.state = "CONFIRMING"
                cat_unit.start_detect_ts = now
                print("Cat spotted... starting 3s confirmation.")

        # STATE: CONFIRMING (Checking if cat stays for 3s)
        elif cat_unit.state == "CONFIRMING":
            if not cat_detected:
                cat_unit.state = "IDLE"
                print("Cat left. Confirmation reset.")
            elif (now - cat_unit.start_detect_ts) >= CONFIRMATION_TIME:
                print("Cat confirmed. Opening Lid.")
                send_serial("OPEN_LID")
                cat_unit.lid_open = True
                cat_unit.state = "OPEN"
                cat_unit.timeout_ts = now + FEEDING_WINDOW

        # STATE: OPEN (10-minute timer)
        elif cat_unit.state == "OPEN":
            # If cat is seen, reset/extend the 10-minute timer
            if cat_detected:
                cat_unit.timeout_ts = now + FEEDING_WINDOW
            
            # Close if 10m is up AND cat is no longer there
            if now > cat_unit.timeout_ts and not cat_detected:
                print("10m Feeding window expired. Closing Lid.")
                send_serial("CLOSE_LID")
                cat_unit.lid_open = False
                cat_unit.state = "IDLE"

        # 3. MANUAL FEED REQUESTS (from App)
        node = dispenser_cat_ref.get() or {}
        run = bool(node.get("run", False))
        amount = float(node.get("amount", 0) or 0)

        if run and not cat_unit.last_run_state:
            print(f"FEED REQUEST RECEIVED: {amount}g")
            set_status("starting")
            
            # Ensure lid is open for dispensing
            if not cat_unit.lid_open:
                send_serial("OPEN_LID")
                cat_unit.lid_open = True
                cat_unit.state = "OPEN" # Move to open state so timer starts
                cat_unit.timeout_ts = now + FEEDING_WINDOW
                time.sleep(1.0) 

            send_serial(f"DISPENSE {amount}")
            cat_unit.is_dispensing = True

        cat_unit.last_run_state = run
        time.sleep(POLL_INTERVAL)

# ----------------- START -----------------
threading.Thread(target=serial_listener, daemon=True).start()
print("RTDB CAT FSM CONTROLLER STARTED")

try:
    rtdb_loop()
except KeyboardInterrupt:
    print("Exiting.")
    if cat_unit.lid_open:
        send_serial("CLOSE_LID")