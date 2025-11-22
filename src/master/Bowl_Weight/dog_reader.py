from dog_weight_reader import DogWeightReader
from firebase_dog import FirebaseDogUploader
import time

reader = DogWeightReader()
firebase = FirebaseDogUploader()

print("DOG bowl weight system running...")

while True:
    weight = reader.get_weight()

    if weight is not None:
        print("DOG Weight:", weight)
        firebase.upload(weight)

    time.sleep(0.1)
