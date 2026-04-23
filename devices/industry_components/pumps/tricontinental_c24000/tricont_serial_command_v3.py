import serial
import time

with serial.Serial(port='COM15', baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=3) as ser:
    ser.flushInput()
    ser.write(b'/2TR\r')
    time.sleep(0.5)
    ser.flushInput()
    #ser.write(b'/2zR\r')
    #time.sleep(1)
    #ser.flushInput()
    ser.write(b'/2Z15R\r')
    time.sleep(0.5)
    ser.flushInput()
    #for i in range(30):
    #    ser.write(b'/2Q\r')
    #    time.sleep(0.5)
    #    response = ser.read_until(b'\r')
    #    print(response.decode(errors='replace').strip())
    #ser.write(b'/2zR\r')
    #time.sleep(1)
    #ser.flushInput()
    ser.write(b'/2A24000R\r')
    time.sleep(1)
    ser.flushInput()
    '''
    for i in range(15):
        command = f"2s{i}R\r".encode()
        ser.write(command)
        time.sleep(0.5)
        ser.flushInput()
    '''