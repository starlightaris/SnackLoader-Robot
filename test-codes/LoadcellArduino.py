from hx711 import HX711
import time


DT = 3    # GPIO 3
SCK = 2   # GPIO 2

# Initialize sensor
scale = HX711(dout_pin=DT, pd_sck_pin=SCK)

calibration_factor = 7050   # adjust after calibration


scale.reset()
scale.tare()

print("Scale ready...")

while True:
    # Read average of 10 samples
    reading = scale.get_weight_mean(10)

    # Convert to kilograms
    weight = reading / calibration_factor

    # Force positive
    if weight < 0:
        weight = -weight

    print(f"Weight: {weight:.3f} kg")

    time.sleep(0.3)
