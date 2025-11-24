from temp_reader import TemperatureReader
from firebase_temp import FirebaseTemperature
import time

reader = TemperatureReader()
firebase = FirebaseTemperature()

print("Temperature system running...")

while True:
    temp, hum = reader.read()

    if temp is not None:
        print(f"Temp: {temp}°C | Humidity: {hum}%")
        firebase.upload(temp, hum)

    time.sleep(1)
