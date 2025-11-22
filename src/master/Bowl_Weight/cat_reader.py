from cat_weight_reader import CatWeightReader
from firebase_cat import FirebaseCatUploader
import time

reader = CatWeightReader()
firebase = FirebaseCatUploader()

print("CAT bowl weight system running...")

while True:
    weight = reader.get_weight()

    if weight is not None:
        print("CAT Weight:", weight)
        firebase.upload(weight)

    time.sleep(0.1)
