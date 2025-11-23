import serial, time, threading
import firebase_admin
from firebase_admin import credentials, db

# ---------- CONFIG ----------
SERVICE_ACCOUNT = "/home/eutech/serviceAccountKey.json"
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app"

ARDUINO_PORT = "/dev/ttyUSB1"      # update if needed
BAUD = 9600

GRACE_PERIOD_AFTER_DONE = 10.0     # 60s grace after dispensing
POLL_INTERVAL = 0.25               # check every 250ms

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
last_closed_by_dog = False

cat_present = False
dog_present = False
last_arduino_message = ""
last_weight = None

# ---------------------------------------------------------
# HELPERS
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
    global is_dispensing, after_done_open_until, last_arduino_message
    global lid_is_open, last_closed_by_dog, last_weight

    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line:
            continue

        last_arduino_message = line
        print("[ARDUINO]", line)

        # LIVE weight
        if line.startswith("LIVE"):
            try:
                w = float(line.split()[1])
                upload_weight(w)
            except:
                pass

        # Final weight
        elif line.startswith("WEIGHT"):
            try:
                w = float(line.split()[1])
                upload_weight(w)
            except:
                pass

        # Dispense done
        elif line == "DONE":
            is_dispensing = False
            set_status("completed")
            db.reference("dispenser/cat").update({"run": False})
            after_done_open_until = time.time() + GRACE_PERIOD_AFTER_DONE
            print("Feeding complete — lid open during 60s grace.")

        # Lid opened
        elif line == "OPEN":
            lid_is_open = True
            last_closed_by_dog = False

        # Lid closed
        elif line in ("CLOSED", "FORCED_CLOSED"):
            lid_is_open = False
            if line == "FORCED_CLOSED":
                last_closed_by_dog = True

# ---------------------------------------------------------
# MAIN LOGIC LOOP
# ---------------------------------------------------------
def control_loop():
    global is_dispensing, after_done_open_until, cat_present, dog_present
    global lid_is_open, last_closed_by_dog

    last_run = False

    while True:
        cat_present, dog_present = read_detection()

        node = db.reference("dispenser/cat").get() or {}
        run = node.get("run", False)
        amount = float(node.get("amount", 0) or 0)

        # --------------------------------------------
        # DURING DISPENSING → dog interrupts
        # --------------------------------------------
        if is_dispensing and dog_present:
            print("DOG detected during dispensing -> CLOSE immediately")
            ser.write(b"CLOSE\n")
            set_status("aborted_dog_detected")
            is_dispensing = False
            last_closed_by_dog = True
            db.reference("dispenser/cat").update({"run": False})

        # --------------------------------------------
        # Special rule  (your request)
        # If lid closed due to dog & cat appears → open lid
        # EVEN IF the dog is also detected
        # --------------------------------------------
        if last_closed_by_dog and cat_present:
            print("Cat detected after dog close → reopening lid now.")
            ser.write(b"OPEN\n")
            set_status("reopened_after_dog_close_for_cat")
            last_closed_by_dog = False
            time.sleep(0.2)

        # --------------------------------------------
        # START DISPENSE → ALWAYS ALLOWED
        # --------------------------------------------
        if run and not last_run:
            print("Dispense request:", amount, "g")

            # Step 1: open lid
            ser.write(b"OPEN\n")
            set_status("opening")

            # Wait for Arduino OPEN
            t0 = time.time()
            while time.time() - t0 < 1.0:
                if last_arduino_message == "OPEN" or lid_is_open:
                    break
                time.sleep(0.05)

            # Step 2: send DISPENSE
            ser.write(f"DISPENSE {amount}\n".encode())
            is_dispensing = True
            set_status("feeding")
            print("DISPENSE sent.")

        # --------------------------------------------
        # AFTER DISPENSING → 60s GRACE
        # --------------------------------------------
        if after_done_open_until:
            now = time.time()

            # dog appears during grace → close immediately
            if dog_present:
                print("DOG detected during grace → closing lid.")
                ser.write(b"CLOSE\n")
                after_done_open_until = None
                lid_is_open = False
                last_closed_by_dog = True

            # cat stays → extend 60s
            elif cat_present:
                after_done_open_until = now + GRACE_PERIOD_AFTER_DONE

            # cat absent → close after timeout
            elif now >= after_done_open_until:
                print("Grace expired → closing lid.")
                ser.write(b"CLOSE\n")
                after_done_open_until = None
                lid_is_open = False

        last_run = run
        time.sleep(POLL_INTERVAL)

# ---------------------------------------------------------
# RUN THREADS
# ---------------------------------------------------------
threading.Thread(target=serial_listener, daemon=True).start()
threading.Thread(target=control_loop, daemon=True).start()

print("Feeder controller running (final, frontend-safe).")
while True:
    time.sleep(1)
