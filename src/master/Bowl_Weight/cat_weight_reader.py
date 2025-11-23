# cat_weight_reader.py
import serial, time

class CatWeightReader:
    def __init__(self, port="/dev/ttyUSB0", baud=9600):
        self.port = port; self.baud = baud; self.serial = None
        self.connect()

    def connect(self):
        try:
            self.serial = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(2)
            print(f"[CAT] Serial connected to {self.port}")
        except Exception as e:
            print(f"[CAT] Serial connect error: {e}")
            self.serial = None

    def get_weight(self):
        if not self.serial:
            self.connect(); return None
        try:
            if self.serial.in_waiting > 0:
                line = self.serial.readline().decode().strip()
                return float(line)
        except Exception:
            return None
        return None
