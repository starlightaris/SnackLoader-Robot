import serial
import serial.tools.list_ports
import time

# --------- Auto-find Arduino port ---------
def find_arduino():
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if "Arduino" in p.description or "ttyUSB" in p.device or "ttyACM" in p.device:
            return p.device
    return None

arduino_port = find_arduino()
if arduino_port is None:
    print("Arduino not found! Connect it and run again.")
    exit()

print(f"Arduino found at: {arduino_port}")

# --------- Open Serial ---------
arduino = serial.Serial(arduino_port, 9600, timeout=1)
time.sleep(2)  # give Arduino time to reset

# --------- Helper functions ---------
def send(cmd):
    """Send command to Arduino."""
    arduino.write((cmd + "\n").encode())
    print(f"[SEND] {cmd}")

def read_response(timeout=2):
    """Read lines from Arduino for given timeout in seconds."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        while arduino.in_waiting > 0:
            line = arduino.readline().decode().strip()
            if line:
                print("[ARDUINO]", line)

# --------- Test Menu ---------
def menu():
    print("\n=== ARDUINO TEST MENU ===")
    print("1) CAT (open bowl)")
    print("2) DISPENSE")
    print("3) MAX_WEIGHT + DISPENSE")
    print("4) WEIGHT")
    print("5) CLOSE_ALL")
    print("0) Exit")
    print("==========================")

# --------- Main Loop ---------
while True:
    menu()
    choice = input("Choose test: ")

    if choice == "1":
        send("CAT")
        time.sleep(1)
        read_response()

    elif choice == "2":
        send("DISPENSE")
        time.sleep(1)
        read_response()

    elif choice == "3":
        weight = input("Enter max weight (grams): ")
        send(f"MAX_WEIGHT:{weight}")
        time.sleep(1)
        read_response()
        send("DISPENSE")
        time.sleep(1)
        read_response()

    elif choice == "4":
        send("WEIGHT")
        time.sleep(1)
        read_response()

    elif choice == "5":
        send("CLOSE_ALL")
        time.sleep(1)
        read_response()

    elif choice == "0":
        print("Exiting.")
        break

    else:
        print("Invalid choice. Try again.")

    time.sleep(0.5)
