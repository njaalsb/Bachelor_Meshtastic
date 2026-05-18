import time
import serial

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

while True:
    # Wait for signal from ESP32
    data = ser.read()
