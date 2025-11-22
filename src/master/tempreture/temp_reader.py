import serial
import time

class TemperatureReader:
    def __init__(self, port="/dev/ttyACM0", baud=9600):
        self.serial = serial.Serial(port, baud, timeout=1)
        time.sleep(2)

    def read(self):
        if self.serial.in_waiting > 0:
            line = self.serial.readline().decode().strip()
            if "," in line:
                t, h = line.split(",")
                return float(t), float(h)
        return None, None
