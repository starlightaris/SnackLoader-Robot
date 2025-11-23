import serial, time, threading
import firebase_admin
from firebase_admin import credentials, db

# ---------- CONFIG ----------
SERVICE_ACCOUNT = "/home/eutech/serviceAccountKey.json"
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app"

ARDUINO_PORT = "/dev/ttyUSB1"   # change if needed
BAUD = 9600

GRACE_PERIOD_AFTER_DONE = 60.0  
POLL_INTERVAL = 0.25            

# ---------- INIT FIREBASE ----------
cred = credentials.Certificate(SERVICE_ACCOUNT)
firebase_admin.initialize_app(cred, {"databaseURL": RTDB_URL})

# ---------- SERIAL ----------
ser = serial.Serial(ARDUINO_PORT, BAUD, timeout=1)
time.sleep(2)

# ---------- GLOBAL FLAGS ----------
is_dispensing = False
after_done_open_until = None
cat_present = False
dog_present = False

last_arduino_message = ""

def upload_weight(weight):
    db.reference("petfeeder/cat/bowlWeight").update({
        "weight": float(weight),
        "unit": "g",
        "timestamp": int(time.time())
    })

def set_status(status):
    db.reference("dispenser/cat").update({"status": status})

def read_detection():
    d = db.reference("detectionStatus").get() or {}
    cat = d.get("cat", {}).get("detected", False)
    dog = d.get("dog", {}).get("detected", False)
    return bool(cat), bool(dog)

# ---------------- SERIAL LISTENER ----------------
def serial_listener():
    global is_dispensing, after_done_open_until, last_arduino_message

    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue

        last_arduino_message = line
        print("[ARDUINO]", line)

        if line.startswith("LIVE"):
            w = float(line.split()[1])
            upload_weight(w)

        elif line.startswith("WEIGHT"):
            w = float(line.split()[1])
            upload_weight(w)

        elif line == "DONE":
            is_dispensing = False
            set_status("completed")
            db.reference("dispenser/cat").update({"run": False})
            after_done_open_until = time.time() + GRACE_PERIOD_AFTER_DONE
            print("Feeding complete — Lid remains open during grace period.")

        elif line == "FORCED_CLOSED":
            set_status("forced_closed")
            after_done_open_until = None

# ---------------- MAIN LOGIC ----------------
def control_loop():
    global is_dispensing, after_done_open_until, cat_present, dog_present, last_arduino_message

    last_run = False

    while True:
        cat_present, dog_present = read_detection()

        node = db.reference("dispenser/cat").get() or {}
        run = node.get("run", False)
        amount = float(node.get("amount", 0))

        # ---- START DISPENSE REQUEST ----
        if run and not last_run:
            print("Feed request:", amount, "grams")

            # STEP 1: Open lid FIRST
            print("Opening lid before dispensing...")
            ser.write(b"OPEN\n")
            set_status("opening")

            # Wait for Arduino confirmation
            t0 = time.time()
            while time.time() - t0 < 1.0:  # wait up to 1 second
                if last_arduino_message == "OPEN":
                    print("Arduino confirmed: Lid is OPEN")
                    break
                time.sleep(0.05)

            # STEP 2: Send DISPENSE command
            ser.write(f"DISPENSE {amount}\n".encode())
            is_dispensing = True
            set_status("feeding")
            print("Sent DISPENSE command.")

        # ---- DURING DISPENSE ----
        if is_dispensing:
            if dog_present:
                print("Dog detected → FORCE CLOSE immediately!")
                ser.write(b"CLOSE\n")
                set_status("aborted_dog_detected")
                is_dispensing = False

        # ---- AFTER DISPENSE (LID OPEN) ----
        if after_done_open_until:
            now = time.time()

            if dog_present:
                print("Dog detected → FORCE CLOSE")
                ser.write(b"CLOSE\n")
                after_done_open_until = None

            elif not cat_present and now >= after_done_open_until:
                print("Cat absent for 60s → closing lid")
                ser.write(b"CLOSE\n")
                after_done_open_until = None

            elif cat_present:
                # keep the lid open while cat stays
                after_done_open_until = now + GRACE_PERIOD_AFTER_DONE

        last_run = run
        time.sleep(POLL_INTERVAL)

# ---------------- START THREADS ----------------
threading.Thread(target=serial_listener, daemon=True).start()
threading.Thread(target=control_loop, daemon=True).start()

print("Feeder controller running...")
while True:
    time.sleep(1)
