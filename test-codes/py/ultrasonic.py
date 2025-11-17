import serial
import time

try:
    arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    time.sleep(2)
    print("Connected to Arduino")
except Exception as e:
    print(f"Connection failed: {e}")
    exit()

def read_distance():
    try:
        if arduino.in_waiting > 0:
            line = arduino.readline().decode('utf-8').rstrip()
            if line.startswith("DISTANCE:"):
                distance = int(line.split(':')[1])
                return distance
            else:
                try:
                    return int(line)
                except:
                    return None
    except Exception as e:
        print(f"Read error: {e}")
        return None

try:
    while True:
        distance = read_distance()
        if distance is not None:
            if distance == -1 or distance == 999:
                print("No object detected or sensor timeout")
            else:
                print(f"Distance: {distance} cm")
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nExiting...")
    arduino.close()