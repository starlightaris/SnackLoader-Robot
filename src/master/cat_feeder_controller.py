import serial
import time
import threading
import firebase_admin
from firebase_admin import credentials, db

# --- CONFIG ---
SERVICE_ACCOUNT = "/home/eutech/serviceAccountKey.json"
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"

PORT = "/dev/ttyUSB0"  # Change this to match the Cat Arduino's port
BAUD = 9600
POLL_INTERVAL = 0.5    # 0.5s is plenty for a 10-min timer logic

# --- FSM SETTINGS ---
CONFIRMATION_TIME = 3    # Seconds cat must be present to open
FEEDING_WINDOW = 600     # 10 minutes (600 seconds)

# --- INIT FIREBASE ---
cred = credentials.Certificate(SERVICE_ACCOUNT)
firebase_admin.initialize_app(cred, {"databaseURL": RTDB_URL})

# --- SERIAL ---
try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
except Exception as e:
    print("Serial open error:", e)
    ser = None

# --- FIREBASE REFERENCES ---
dispenser_cat_ref = db.reference("dispenser/cat")
petfeeder_cat_ref = db.reference("petfeeder/cat/bowlWeight")
det_ref = db.reference("detectionStatus")

# --- GLOBAL STATE ---
class CatSystem:
    def __init__(self):
        self.state = "IDLE"           # IDLE, CONFIRMING, OPEN
        self.lid_is_open = False
        self.start_detect_ts = 0      # When did we first see the cat?
        self.timeout_ts = 0           # When should the lid close?
        self.is_dispensing = False
        self.last_run_state = False

cat = CatSystem()

# --- HELPERS ---
def send_serial(cmd: str):
    if ser and ser.is_open:
        ser.write((cmd + "\n").encode())
        print(f"[SEND] {cmd}")

def serial_listener():
    while True:
        if ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode(errors="ignore").strip()
                if line.startswith("LIVE"):
                    # Update weight to Firebase
                    weight = line.split()[1]
                    petfeeder_cat_ref.update({"weight": float(weight), "timestamp": int(time.time())})
                if line == "DONE":
                    cat.is_dispensing = False
                    dispenser_cat_ref.update({"status": "completed", "run": False})
            except: pass
        time.sleep(0.01)

# --- FINITE STATE MACHINE LOGIC ---
def update_fsm(is_detected):
    now = time.time()

    # STATE: IDLE (Lid Closed, looking for cat)
    if cat.state == "IDLE":
        if is_detected:
            cat.state = "CONFIRMING"
            cat.start_detect_ts = now
            print("Cat spotted... confirming (3s)")

    # STATE: CONFIRMING (Waiting for 3s of continuous presence)
    elif cat.state == "CONFIRMING":
        if not is_detected:
            cat.state = "IDLE"
            print("Cat left during confirmation. Resetting.")
        elif (now - cat.start_detect_ts) >= CONFIRMATION_TIME:
            print("Confirmation complete. Opening Lid.")
            send_serial("OPEN_LID")
            cat.lid_is_open = True
            cat.state = "OPEN"
            cat.timeout_ts = now + FEEDING_WINDOW

    # STATE: OPEN (Lid stays open for 10 mins)
    elif cat.state == "OPEN":
        # RESET TIMER: If cat is seen, push the timeout forward
        if is_detected:
            cat.timeout_ts = now + FEEDING_WINDOW
        
        # CLOSE CONDITION: Timer expired AND cat is not currently there
        if now > cat.timeout_ts:
            if not is_detected:
                print("10m Timeout & Cat gone. Closing Lid.")
                send_serial("CLOSE_LID")
                cat.lid_is_open = False
                cat.state = "IDLE"
            else:
                # Cat is still there, extend by another minute or stay open
                pass 

def main_loop():
    while True:
        # 1. Get Detection Status
        det = det_ref.get() or {}
        cat_present = bool(det.get("cat", {}).get("detected", False))
        
        # 2. Update the FSM
        update_fsm(cat_present)

        # 3. Handle Dispenser "Run" button from App
        node = dispenser_cat_ref.get() or {}
        run_val = bool(node.get("run", False))
        if run_val and not cat.last_run_state:
            amount = node.get("amount", 0)
            if not cat.lid_is_open:
                send_serial("OPEN_LID")
                cat.lid_is_open = True
                time.sleep(1) # Wait for stepper
            send_serial(f"DISPENSE {amount}")
            cat.is_dispensing = True
        cat.last_run_state = run_val

        time.sleep(POLL_INTERVAL)

# --- START ---
threading.Thread(target=serial_listener, daemon=True).start()
print("Cat Unit FSM Started...")
try:
    main_loop()
except KeyboardInterrupt:
    if cat.lid_is_open:
        send_serial("CLOSE_LID")