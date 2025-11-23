# feeder_pi_controller.py
import serial, time, threading, os
import firebase_admin
from firebase_admin import credentials, db

SERVICE_ACCOUNT = os.path.expanduser("/home/pi/SnackLoader-Robot/firebase/serviceAccountKey.json")
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app"

if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT)
    firebase_admin.initialize_app(cred, {"databaseURL": RTDB_URL})

# Update these serial ports to match your Pi devices (use `dmesg` to check)
ARDUINO_PORT_CAT = "/dev/ttyUSB0"
ARDUINO_PORT_DOG = "/dev/ttyACM0"  # optional

BAUD = 9600

def open_serial(port):
    try:
        ser = serial.Serial(port, BAUD, timeout=1)
        time.sleep(2)
        print("Connected to", port)
        return ser
    except Exception as e:
        print("Serial open error:", e)
        return None

ser_cat = open_serial(ARDUINO_PORT_CAT)
ser_dog = open_serial(ARDUINO_PORT_DOG)

def get_bowl_weight(pet):
    v = db.reference(f"petfeeder/{pet}/bowlWeight/weight").get()
    try:
        return float(v) if v is not None else 0.0
    except:
        return 0.0

def send_cmd_wait_done(ser, cmd, timeout=60):
    if ser is None:
        print("Serial missing")
        return False
    ser.write((cmd + "\n").encode())
    print("[PI -> ARDUINO]", cmd)
    start = time.time()
    while True:
        line = ser.readline().decode().strip()
        if line:
            print("[ARDUINO -> PI]", line)
            if line.upper() == "DONE":
                return True
        if time.time() - start > timeout:
            print("Timeout waiting for DONE")
            return False

def process_feed(pet, ser, amount):
    path = f"dispenser/{pet}"
    db.reference(path).update({"status": "starting"})
    bowl = get_bowl_weight(pet)
    print(f"[{pet}] bowl={bowl}g requested={amount}g")
    if bowl >= amount:
        msg = f"Bowl has {bowl}g which is >= requested {amount}g"
        db.reference(path).update({"status": "too_much_food", "error": msg})
        db.reference(path + "/run").set(False)
        return
    needed = round(amount - bowl, 1)
    db.reference(path).update({"status": "feeding", "needed": needed})
    cmd = f"true {needed}"
    ok = send_cmd_wait_done(ser, cmd)
    if ok:
        db.reference(path).update({"status": "completed", "lastFed": int(time.time())})
    else:
        db.reference(path).update({"status": "error", "error": "arduino_timeout"})
    db.reference(path + "/run").set(False)

def listen_loop():
    print("Feeder controller listening...")
    last_cat_run = False
    last_dog_run = False
    while True:
        cat_node = db.reference("dispenser/cat").get() or {}
        dog_node = db.reference("dispenser/dog").get() or {}
        cat_run = cat_node.get("run", False)
        dog_run = dog_node.get("run", False)
        if cat_run and not last_cat_run:
            amount = float(cat_node.get("amount", 0))
            threading.Thread(target=process_feed, args=("cat", ser_cat, amount), daemon=True).start()
        if dog_run and not last_dog_run:
            amount = float(dog_node.get("amount", 0))
            threading.Thread(target=process_feed, args=("dog", ser_dog, amount), daemon=True).start()
        last_cat_run = cat_run
        last_dog_run = dog_run
        time.sleep(0.3)

if __name__ == "__main__":
    listen_loop()
