import subprocess
import signal
import os

process = None

def start_camera():
    global process
    if process is None:
        print("Starting camera...")

        # This resolves to:
        # /home/pi/SnackLoader-Robot/src/master/raspberry.py
        script_path = os.path.join(os.path.dirname(__file__), "raspberry.py")

        process = subprocess.Popen(["python3", script_path])

def stop_camera():
    global process
    if process is not None:
        print("Stopping camera...")
        process.send_signal(signal.SIGTERM)
        process = None
