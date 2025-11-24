import time
import firebase_admin
from firebase_admin import credentials, db

class FirebaseTemperature:
    def __init__(self):
        cred = credentials.Certificate("/home/eutech/serviceAccountKey.json")
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"
        })
        self.ref = db.reference("temperature")

    def upload(self, temp, hum):
        self.ref.set({
            "temperature": temp,
            "humidity": hum,
            "timestamp": int(time.time())
        })
