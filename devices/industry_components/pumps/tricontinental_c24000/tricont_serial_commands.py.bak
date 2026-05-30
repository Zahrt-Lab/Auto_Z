import serial
import time

with serial.Serial(port='COM15', baudrate=9600, bytesize=8,
                   parity='N', stopbits=1, timeout=3) as ser:

    #ser.flushInput()
    #ser.write(b'/1TR\r')
    #time.sleep(0.5)
    #ser.flushInput()

    ser.flushInput()
    ser.write(b'/2TR\r')
    time.sleep(0.5)
    ser.flushInput()

    #time.sleep(1)
    #ser.write(b'/1ZR\r')
    time.sleep(1)
    ser.write(b'/2ZR\r')

    #print("Sending init command...")
    #ser.write(b'/2V2000IA24000R\r')

    print("Waiting for response...")