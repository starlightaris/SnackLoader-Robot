import RPi.GPIO as GPIO
import time
import sys

# HX711 pins
DT = 5   # GPIO 5 (Physical pin 29)
SCK = 6  # GPIO 6 (Physical pin 31)

class HX711:
    def __init__(self, dout, pd_sck):
        self.DOUT = dout
        self.PD_SCK = pd_sck
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.PD_SCK, GPIO.OUT)
        GPIO.setup(self.DOUT, GPIO.IN)
        
        self.OFFSET = 0
        self.SCALE = 1
        
    def read(self):
        # Wait for DOUT to go low indicating data is ready
        while GPIO.input(self.DOUT) == 1:
            time.sleep(0.001)
        
        data = 0
        # Read 24 bits
        for _ in range(24):
            GPIO.output(self.PD_SCK, True)
            data <<= 1
            GPIO.output(self.PD_SCK, False)
            if GPIO.input(self.DOUT):
                data |= 1
        
        # Set channel and gain for next reading
        for _ in range(1):
            GPIO.output(self.PD_SCK, True)
            GPIO.output(self.PD_SCK, False)
        
        # Convert from two's complement
        if data & 0x800000:
            data -= 0x1000000
        
        return data
    
    def get_weight(self, samples=5):
        total = 0
        for _ in range(samples):
            total += self.read()
            time.sleep(0.01)
        
        # Adjust with calibration values
        return (total / samples - self.OFFSET) / self.SCALE
    
    def tare(self, samples=10):
        # Set current reading as zero point
        total = 0
        for _ in range(samples):
            total += self.read()
            time.sleep(0.01)
        self.OFFSET = total / samples
        print(f"Tare completed. Offset: {self.OFFSET}")
    
    def calibrate(self, known_weight):
        # Calibrate with known weight
        print("Remove all weight from scale and press Enter...")
        input()
        self.tare()
        
        print(f"Place {known_weight}g weight on scale and press Enter...")
        input()
        
        raw_value = 0
        for _ in range(10):
            raw_value += self.read()
            time.sleep(0.01)
        raw_value = raw_value / 10
        
        self.SCALE = (raw_value - self.OFFSET) / known_weight
        print(f"Calibration completed. Scale factor: {self.SCALE}")

# Create HX711 instance
hx = HX711(DT, SCK)

try:
    print("HX711 Load Cell Test")
    print("Press Ctrl+C to exit")
    
    # Tare the scale (set zero)
    print("Taring scale... remove any weight")
    time.sleep(2)
    hx.tare()
    
    # If you have a known weight, you can calibrate:
    # hx.calibrate(1000)  # Calibrate with 1000g weight
    
    while True:
        weight = hx.get_weight()
        print(f"Weight: {weight:.2f} raw units")
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nExiting...")
    GPIO.cleanup()
    sys.exit()