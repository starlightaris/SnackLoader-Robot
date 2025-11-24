import serial
import time
import firebase_admin
from firebase_admin import credentials, db

# ---------------------------------------------------------
# 1. FIREBASE SETUP
# ---------------------------------------------------------
cred = credentials.Certificate("/home/eutech/serviceAccountKey.json")

firebase_admin.initialize_app(cred, {
    "databaseURL": "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"
})

temp_ref = db.reference("temperature")


# ---------------------------------------------------------
# 2. CONNECT TO ARDUINO
# ---------------------------------------------------------
def connect_serial(port="/dev/ttyACM0", baud=9600):
    ser = serial.Serial(port, baud, timeout=1)
    time.sleep(2)
    return ser


# ---------------------------------------------------------
# 3. MAIN LOOP – Upload every 120 seconds
# ---------------------------------------------------------
def main():
    print("Temperature monitoring started (uploading every 2 minutes)...")

    ser = connect_serial()
    last_upload_time = 0
    latest_temp = None
    latest_hum = None

    while True:
        # Read Arduino
        if ser.in_waiting > 0:
            line = ser.readline().decode().strip()

            if "," in line:
                try:
                    t, h = line.split(",")
                    latest_temp = float(t)
                    latest_hum = float(h)

                    print(f"Latest Reading → Temp: {latest_temp}°C | Hum: {latest_hum}%")

                except:
                    pass

        # Upload only every 2 minutes (120 seconds)
        if time.time() - last_upload_time >= 120 and latest_temp is not None:
            print("Uploading to Firebase...")
            temp_ref.set({
                "temperature": latest_temp,
                "humidity": latest_hum,
                "timestamp": int(time.time())
            })

            last_upload_time = time.time()
            print("Uploaded ✔")

        time.sleep(1)


if __name__ == "__main__":
    main()
