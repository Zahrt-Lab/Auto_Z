import serial
import time

with serial.Serial(port='COM15', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=3) as ser:
    ser.flushInput()
    ser.write(b'/2TR\r')
    time.sleep(0.5)
    ser.flushInput()
    ser.write(b'/2ZR\r')
    time.sleep(30)
    response = ser.read_until(b'\x0a')  # reads until Line Feed
    print(response)