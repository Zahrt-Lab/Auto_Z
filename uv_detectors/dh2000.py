#------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

'''
The purpose of this script is to control the TTL of the light box
so we can turn the light source off on the UV detector
this is template code before we incorporate it into the AutoZahrt_v3 general methods.

This code will serve the following purposes
1) This will be used to calibrate instruments between runs to ensure accuracy between runs
2) Will be used as a fail/safe if the UV-detector is detecting unusual readings that aren't excepected it's likely an issue and the this will allow the equipment and light source to turn off
3) In experiments that initially need the UV-detector but during the run doesn't need the use of the UV-detector for 30 minutes
'''

import time
import serial
class DH2000:
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 2.0, ):
        self.ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)
        # Arduino resets on connect; give it time
        time.sleep(2.0)
        # Clear startup banner lines (READY text etc.)
        self._drain()
    def _drain(self):
        """Read and discard any pending lines."""
        end = time.time() + 0.5
        while time.time() < end:
            while self.ser.in_waiting:
                self.ser.readline()
            time.sleep(0.01)
    def _read_ok(self) -> None:
        """
        Read lines until we see 'OK' or timeout.
        Some sketches print banner text; ignore it.
        """
        deadline = time.time() + (self.ser.timeout or 2.0)
        while time.time() < deadline:
            line = self.ser.readline().decode("utf-8", errors="ignore").strip()
            if not line:
                continue
            if line == "OK":
                return
            # ignore other chatter (banner, debug, etc.)
        raise RuntimeError("Timed out waiting for OK from Arduino")
    def _cmd_char(self, c: str) -> None:
        if not isinstance(c, str) or len(c) != 1:
            raise ValueError("Command must be a single character like 'o', 'c', 'h', 'd', 'x', 'l'")
        self.ser.write((c + "\n").encode("ascii"))
        self.ser.flush()
        self._read_ok()
    # ---- Public API ----
    def shutter_open(self):
        self._cmd_char("o")
    def shutter_close(self):
        self._cmd_char("c")
    def halogen_toggle(self):
        self._cmd_char("h")
    def deuterium_toggle(self):
        self._cmd_char("d")
    def leds_off(self):
        self._cmd_char("l")
    def calibration_cycle(self, warmup_ms: int = 2000, measure_ms: int = 1000):
        """
        Your current Arduino sketch hard-codes calibrationCycle(2000, 1000)
        when it receives 'x'. So these parameters are not used unless you
        also update the Arduino code to accept them.
        """
        self._cmd_char("x")
    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass
if __name__ == "__main__":
    port = "/dev/ttyACM0"
    print(f"Running DH2000 timed sequence on {port}...")
    dh = None
    try:
        dh = DH2000(port, )
        print("Connected successfully!")
        dh.leds_off()   # disable LEDs now that the link is up
        # Make sure shutter is closed before starting
        print("Ensuring shutter is closed...")
        dh.shutter_close()
        time.sleep(0.5)
        # 1) Turn both lamps on
        print("Turning BOTH lamps ON...")
        dh.halogen_toggle()
        time.sleep(0.2)
        dh.deuterium_toggle()
        print("Waiting 15 seconds with lamps ON, shutter CLOSED...")
        time.sleep(15)
        # 2) Open shutter for 15 seconds
        print("Opening shutter...")
        dh.shutter_open()
        print("Waiting 15 seconds with lamps ON, shutter OPEN...")
        time.sleep(15)
        # 3) Close shutter and turn both lamps off
        print("Closing shutter...")
        dh.shutter_close()
        time.sleep(0.2)
        print("Turning BOTH lamps OFF...")
        dh.halogen_toggle()
        time.sleep(0.2)
        dh.deuterium_toggle()
        print("Sequence complete.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if dh is not None:
            dh.close()
            print("Connection closed.")