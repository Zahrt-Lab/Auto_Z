import serial
import time

with serial.Serial(port='COM15', baudrate=9600, bytesize=8,
                   parity='N', stopbits=1, timeout=3) as ser:

    ser.write(b'/2?19\r')   # 0 = not initialized, 1 = initialized
    ser.write(b'/2?15\r')   # number of init attempts since power cycle
    ser.write(b'/2?76\r')   # pump config: valve type / baud / CAN rate
    ser.write(b'/2?23\r')   # firmware version
    ser.write(b'/2?60\r')   # plunger HOME opto state (0=open, 1=closed) — skip if MP variant
    ser.write(b'/2?21\r')   # encoder calibration levels