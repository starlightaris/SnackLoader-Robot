import time
import firebase_admin
from firebase_admin import credentials, db

class FirebaseDogUploader:
    def __init__(self):
        cred = credentials.Certificate("/home/eutech/serviceAccountKey.json")
        firebase_admin.initialize_app(cred, {
            "databaseURL": "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app/"
        })

        self.ref = db.reference("/petfeeder/dog/bowlWeight")

    def upload(self, grams):
        self.ref.set({
            "weight": grams,
            "unit": "g",
            "timestamp": int(time.time())
        })
