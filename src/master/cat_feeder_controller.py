import serial, time, threading
import firebase_admin
from firebase_admin import credentials, db

# ---------- CONFIG ----------
SERVICE_ACCOUNT = "/home/eutech/serviceAccountKey.json"
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app"

ARDUINO_PORT = "/dev/ttyUSB1"
BAUD = 9600

GRACE_PERIOD_AFTER_DONE = 60.0
POLL_INTERVAL = 0.25

# ---------- INIT FIREBASE ----------
cred = credentials.Certificate(SERVICE_ACCOUNT)
firebase_admin.initialize_app(cred, {"databaseURL": RTDB_URL})

# ---------- SERIAL ----------
ser = serial.Serial(ARDUINO_PORT, BAUD, timeout=1)
time.sleep(2)

# ---------- STATE ----------
is_dispensing = False
after_done_open_until = None

lid_is_open = False
disp_is_open = False
last_closed_by_dog = False

cat_present = False
dog_present = False

last_arduino_message = ""
last_weight = 0

# ---------------------------------------------------------
def upload_weight(weight):
    global last_weight
    last_weight = float(weight)

    db.reference("petfeeder/cat/bowlWeight").update({
        "weight": last_weight,
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

# ---------------------------------------------------------
# LISTEN TO ARDUINO
# ---------------------------------------------------------
def serial_listener():
    global lid_is_open, disp_is_open, last_arduino_message
    global is_dispensing, after_done_open_until, last_closed_by_dog

    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue

        last_arduino_message = line
        print("[ARDUINO]:", line)

        if line.startswith("LIVE"):
            w = float(line.split()[1])
            upload_weight(w)

        elif line.startswith("WEIGHT"):
            w = float(line.split()[1])
            upload_weight(w)

        elif line == "OPEN_LID":
            lid_is_open = True

        elif line == "OPEN_DISP":
            disp_is_open = True

        elif line == "CLOSED_LID":
            lid_is_open = False

        elif line == "CLOSED_DISP":
            disp_is_open = False

        elif line == "DONE":
            is_dispensing = False
            set_status("completed")
            db.reference("dispenser/cat").update({"run": False})
            after_done_open_until = time.time() + GRACE_PERIOD_AFTER_DONE

        elif line == "FORCED_CLOSED":
            lid_is_open = False
            disp_is_open = False
            last_closed_by_dog = True

# ---------------------------------------------------------
# MAIN CONTROL LOOP
# ---------------------------------------------------------
def control_loop():
    global is_dispensing, after_done_open_until
    global lid_is_open, last_closed_by_dog

    last_run = False

    while True:
        cat_present, dog_present = read_detection()

        node = db.reference("dispenser/cat").get() or {}
        run = node.get("run", False)
        amount = float(node.get("amount", 0))

        if run and not last_run:
            print("Feed request:", amount, "g")

            ser.write(b"OPEN\n")
            set_status("opening")

            time.sleep(1.0)

            ser.write(f"DISPENSE {amount}\n".encode())
            is_dispensing = True
            set_status("feeding")

        if is_dispensing and dog_present:
            print("Dog detected → forced close")
            ser.write(b"CLOSE\n")
            set_status("aborted_dog_detected")
            is_dispensing = False
            last_closed_by_dog = True

        if last_closed_by_dog and cat_present:
            print("Cat returned → reopening lid")
            ser.write(b"OPEN\n")
            last_closed_by_dog = False

        if after_done_open_until:
            now = time.time()

            if dog_present:
                print("Dog present → closing lid now")
                ser.write(b"CLOSE\n")
                after_done_open_until = None

            elif cat_present:
                after_done_open_until = now + GRACE_PERIOD_AFTER_DONE

            elif now >= after_done_open_until:
                print("Grace timeout → closing lid")
                ser.write(b"CLOSE\n")
                after_done_open_until = None

        last_run = run
        time.sleep(POLL_INTERVAL)

# ---------------------------------------------------------
threading.Thread(target=serial_listener, daemon=True).start()
threading.Thread(target=control_loop, daemon=True).start()

print("Feeder controller running...")
while True:
    time.sleep(1)
