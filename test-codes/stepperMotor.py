import RPi.GPIO as GPIO
import time

# Pins connected to the motor driver (L293D or ULN2003)
IN1 = 17
IN2 = 18
IN3 = 27
IN4 = 22

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)

# 28BYJ-48 = 2048 steps per 360°
STEPS_PER_REV = 2048

# Step sequence (half-step for smooth motion & torque)
sequence = [
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1],
    [1,0,0,1]
]

def setStep(step):
    GPIO.output(IN1, step[0])
    GPIO.output(IN2, step[1])
    GPIO.output(IN3, step[2])
    GPIO.output(IN4, step[3])

# Rotate any angle
def rotateAngle(angle, direction="CW", rpm=10):
    steps = int((STEPS_PER_REV * angle) / 360.0)

    delay = 60.0 / (rpm * 2048)  # time per step

    if direction == "CW":
        for i in range(steps):
            for step in sequence:
                setStep(step)
                time.sleep(delay)
    else:
        for i in range(steps):
            for step in reversed(sequence):
                setStep(step)
                time.sleep(delay)


try:
    while True:
        print("Rotating 90° CW")
        rotateAngle(90, "CW", rpm=10)
        time.sleep(1)

        print("Rotating 45° CCW")
        rotateAngle(45, "CCW", rpm=10)
        time.sleep(1)

        print("Rotating 180° CW")
        rotateAngle(180, "CW", rpm=10)
        time.sleep(1)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("Program stopped")
