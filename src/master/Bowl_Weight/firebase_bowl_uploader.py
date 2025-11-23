# firebase_bowl_uploader.py
import firebase_admin
from firebase_admin import credentials, db
import time, os

SERVICE_ACCOUNT = os.path.expanduser("/home/eutech/serviceAccountKey.json")
RTDB_URL = "https://snackloader-default-rtdb.asia-southeast1.firebasedatabase.app"

if not firebase_admin._apps:
    cred = credentials.Certificate(SERVICE_ACCOUNT)
    firebase_admin.initialize_app(cred, {"databaseURL": RTDB_URL})

class FirebaseBowlUploader:
    def upload(self, pet, weight):
        path = f"petfeeder/{pet}/bowlWeight"
        try:
            db.reference(path).update({
                "weight": float(weight),
                "unit": "g",
                "timestamp": int(time.time())
            })
        except Exception as e:
            print(f"[Firebase] Upload error for {pet}: {e}")
