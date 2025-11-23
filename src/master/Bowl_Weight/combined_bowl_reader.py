# combined_bowl_reader.py
from cat_weight_reader import CatWeightReader
from dog_weight_reader import DogWeightReader
from firebase_bowl_uploader import FirebaseBowlUploader
import time, statistics

cat_reader = CatWeightReader("/dev/ttyUSB0")
dog_reader = DogWeightReader("/dev/ttyACM0")
firebase = FirebaseBowlUploader()

cat_buf, dog_buf = [], []
last_cat, last_dog = None, None
SMOOTH = 8
CHANGE = 1.0
SLEEP = 0.05

def smooth(buf, v):
    buf.append(v)
    if len(buf) > SMOOTH:
        buf.pop(0)
    return statistics.mean(buf)

print("Combined bowl reader starting...")

while True:
    try:
        cw = cat_reader.get_weight()
        if cw is not None:
            cs = round(smooth(cat_buf, cw), 1)
            if last_cat is None or abs(cs - last_cat) >= CHANGE:
                firebase.upload("cat", cs)
                last_cat = cs
            print("[CAT]", cs, "g")

        dw = dog_reader.get_weight()
        if dw is not None:
            ds = round(smooth(dog_buf, dw), 1)
            if last_dog is None or abs(ds - last_dog) >= CHANGE:
                firebase.upload("dog", ds)
                last_dog = ds
            print("[DOG]", ds, "g")

        time.sleep(SLEEP)
    except KeyboardInterrupt:
        print("Stopped by user")
        break
    except Exception as e:
        print("Reader error:", e)
        time.sleep(1)
