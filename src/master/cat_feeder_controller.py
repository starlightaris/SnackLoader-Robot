# feeder_controller.py — Only Auto-Open When Food Low (clean version)
import serial, time, threading
import firebase_admin
from firebase_admin import credentials, db

# ---------- CONFIG ----------
SERVICE_ACCOUNT = "/home/eutech/serviceAccountKey.json"
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app"

ARDUINO_PORT = "/dev/ttyUSB0"
BAUD = 9600

GRACE_PERIOD_AFTER_DONE = 10.0
POLL_INTERVAL = 0.25

# ---------- AUTO-OPEN LOW FOOD ----------
LOW_FOOD_THRESHOLD = 5.0   # grams — CHANGE HERE
HYSTERESIS = 5.0            # grams above threshold to reset
low_food_triggered = False  # internal flag

# ---------- INIT FIREBASE ----------
cred = credentials.Certificate(SERVICE_ACCOUNT)
firebase_admin.initialize_app(cred, {"databaseURL": RTDB_URL})

# ---------- SERIAL ----------
ser = serial.Serial(ARDUINO_PORT, BAUD, timeout=1)
time.sleep(2)

# ---------- STATE ----------
is_dispensing = False
after_done_open_until = None
last_arduino_message = ""
lid_is_open = False
last_weight = None

cat_present = False
dog_present = False

# ---------- HELPERS ----------
def upload_weight(weight):
    global last_weight
    last_weight = float(weight)
    db.reference("petfeeder/cat/bowlWeight").update({
        "weight": last_weight,
        "unit": "g",
        "timestamp": int(time.time())
    })

def read_detection():
    d = db.reference("detectionStatus").get() or {}
    cat = d.get("cat", {}).get("detected", False)
    dog = d.get("dog", {}).get("detected", False)
    return bool(cat), bool(dog)

def set_status(status):
    db.reference("dispenser/cat").update({"status": status})

# ---------------- SERIAL LISTENER ----------------
def serial_listener():
    global is_dispensing, after_done_open_until, last_arduino_message
    global lid_is_open, last_weight

    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue

        last_arduino_message = line
        print("[ARDUINO]", line)

        if line.startswith("LIVE"):
            try:
                w = float(line.split()[1])
                upload_weight(w)
            except:
                pass

        elif line.startswith("WEIGHT"):
            try:
                w = float(line.split()[1])
                upload_weight(w)
            except:
                pass

        elif line == "DONE":
            is_dispensing = False
            set_status("completed")
            db.reference("dispenser/cat").update({"run": False})

            after_done_open_until = time.time() + GRACE_PERIOD_AFTER_DONE
            print("Feeding DONE — lid open during grace period.")

        elif line == "OPEN":
            lid_is_open = True

        elif line in ["CLOSED", "FORCED_CLOSED"]:
            lid_is_open = False

# ---------------- MAIN CONTROL LOOP ----------------
def control_loop():
    global is_dispensing, after_done_open_until, cat_present, dog_present
    global lid_is_open, low_food_triggered, last_arduino_message

    last_run = False

    while True:
        cat_present, dog_present = read_detection()
        both_present = cat_present and dog_present

        node = db.reference("dispenser/cat").get() or {}
        run = node.get("run", False)
        amount = float(node.get("amount", 0) or 0)
        current_weight = last_weight if last_weight is not None else 0.0

        # ------------------------------------------------------------
        # AUTO-OPEN WHEN FOOD LOW (ONLY SENSOR-BASED FEATURE ADDED)
        # ------------------------------------------------------------
        if (
            current_weight <= LOW_FOOD_THRESHOLD and
            not low_food_triggered and
            not is_dispensing and
            not lid_is_open and
            not dog_present and
            not both_present
        ):
            print(f"Low food ({current_weight}g) → opening lid for refill.")
            ser.write(b"OPEN\n")
            set_status("low_food_open")
            low_food_triggered = True

        # Reset auto-open when food rises above threshold + hysteresis
        if low_food_triggered and current_weight > LOW_FOOD_THRESHOLD + HYSTERESIS:
            low_food_triggered = False

        # ------------------------------------------------------------
        # START DISPENSE REQUEST
        # ------------------------------------------------------------
        if run and not last_run:
            print("Dispense request:", amount, "g")

            ser.write(b"OPEN\n")
            set_status("opening")

            t0 = time.time()
            while time.time() - t0 < 1.0:
                if last_arduino_message == "OPEN":
                    break
                time.sleep(0.05)

            ser.write(f"DISPENSE {amount}\n".encode())
            is_dispensing = True
            set_status("feeding")

        # ------------------------------------------------------------
        # DURING DISPENSING
        # ------------------------------------------------------------
        if is_dispensing and dog_present:
            print("Dog detected during dispense → CLOSE lid!")
            ser.write(b"CLOSE\n")
            is_dispensing = False
            set_status("aborted_dog_detected")

        # ------------------------------------------------------------
        # AFTER DISPENSE — GRACE LOGIC
        # ------------------------------------------------------------
        if after_done_open_until:
            now = time.time()

            if dog_present:
                print("Dog detected after feeding → closing lid.")
                ser.write(b"CLOSE\n")
                after_done_open_until = None

            elif cat_present:
                after_done_open_until = now + GRACE_PERIOD_AFTER_DONE

            elif now >= after_done_open_until:
                print("Cat absent for grace time → closing lid.")
                ser.write(b"CLOSE\n")
                after_done_open_until = None

        last_run = run
        time.sleep(POLL_INTERVAL)

# ---------------- START THREADS ----------------
threading.Thread(target=serial_listener, daemon=True).start()
threading.Thread(target=control_loop, daemon=True).start()

print("Feeder controller running (with auto-open low food)...")
while True:
    time.sleep(1)
