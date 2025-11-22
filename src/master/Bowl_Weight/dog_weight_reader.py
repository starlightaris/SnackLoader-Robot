import serial
import time

class DogWeightReader:
    def __init__(self, port="/dev/ttyUSB0", baud=9600):
        self.serial = serial.Serial(port, baud, timeout=1)
        time.sleep(2)

    def get_weight(self):
        if self.serial.in_waiting > 0:
            try:
                line = self.serial.readline().decode().strip()
                return float(line)
            except:
                return None
        return None
