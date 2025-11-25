import serial
import time
import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate("/home/eutech/serviceAccountKey.json")

firebase_admin.initialize_app(cred, {
    "databaseURL": "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"
})

temp_ref = db.reference("temperature")

def read_temperature_from_arduino(port="/dev/ttyACM1", baud=9600):
    ser = serial.Serial(port, baud, timeout=1)
    time.sleep(2)  # allow Arduino to reset
    return ser

def main():
    print("Starting temperature system...")

    ser = read_temperature_from_arduino()

    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode().strip()

            if "," in line:
                try:
                    t, h = line.split(",")
                    t = float(t)
                    h = float(h)

                    print(f"Temp: {t} °C | Humidity: {h} %")

                    # Upload to Firebase
                    temp_ref.set({
                        "temperature": t,
                        "humidity": h,
                        "timestamp": int(time.time())
                    })

                except:
                    pass  # ignore corrupted readings

        time.sleep(1)


if __name__ == "__main__":
    main()
