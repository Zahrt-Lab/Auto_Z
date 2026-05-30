import serial
import time

with serial.Serial(port='COM15', baudrate=9600, bytesize=8,
                   parity='N', stopbits=1, timeout=3) as ser:
    ser.reset_input_buffer()
    ser.write(b'/2TR\r')              # terminate anything in progress
    time.sleep(0.2)
    ser.reset_input_buffer()

    ser.write(b'/2ZR\r')              # default speed (S11), much faster than Z10
    time.sleep(0.2)
    ser.reset_input_buffer()

    # Poll until idle OR an error appears
    deadline = time.time() + 60       # generous ceiling for a C24000
    while time.time() < deadline:
        ser.write(b'/2Q\r')
        resp = ser.read_until(b'\x03')  # DT replies end with ETX, then CR LF
        # Extract the status byte: it's the char right after "/0"
        idx = resp.find(b'/0')
        if idx >= 0 and len(resp) > idx + 2:
            status = resp[idx + 2]
            busy  = (status & 0x20) == 0      # bit 5 = 0 means busy
            err   = status & 0x0F             # bits 0-3 = error code
            print(f"status=0x{status:02X} busy={busy} err={err}")
            if err != 0:
                raise RuntimeError(f"Pump error code {err} (see Table 7-2, p. 117)")
            if not busy:
                print("Initialization complete.")
                break
        time.sleep(0.25)
    else:
        raise TimeoutError("Pump still busy after 60 s — check ERR LED blink pattern (p. 35)")