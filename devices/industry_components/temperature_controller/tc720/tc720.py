# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

import serial
import time
from typing import Optional, Dict, Union

from ..temperature_controller import TemperatureController

class TC720(TemperatureController):
    def __init__(self, port='COM12', baudrate=230400, timeout=1, name: str = "TC720"):
        self.name = name
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser: Optional[serial.Serial] = None
        self._connected: bool = False

    # ---- Device lifecycle ----------------------------------------------------

    def connect(self) -> None:
        if self.ser and self.ser.is_open:
            self._connected = True
            return
        self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
        self._connected = True
        print(f"Connected to TC-720 on {self.port}")

    def stop(self):
        """Stop the temperature controller device."""
        set_temp = 25.0  # Default safe temperature
        print(f"Stopping TC-720, setting temperature to {set_temp}°C")
        try:
            self.set_temperature(set_temp)
        except Exception as e:
            print(f"Warning: Failed to set safe temperature during stop: {e}")
        self.close()

    # ---- TemperatureController interface --------------------------------------

    def calculate_checksum(self, char_list):
        """
        Calculates the checksum based on the TC-720 command protocol.
        """
        first_6_chars = char_list[1:7]
        total_sum = sum(ord(char) for char in first_6_chars)
        hex_sum = hex(total_sum)[2:]
        last_two_digits = hex_sum[-2:].zfill(2)
        result_list = ['*'] + first_6_chars + list(last_two_digits) + ['\r']
        return result_list

    def convert_temp_to_bstc(self, temp_celsius):
        """
        Converts temperature to the bstc command with checksum for the TC-720 controller.
        """
        temp_hundredths = int(temp_celsius * 100)
        hex_temp = format(temp_hundredths, '04x')
        bstc = ['*', '1', 'c'] + list(hex_temp) + ['XX', 'XX', '\r']
        return self.calculate_checksum(bstc)

    def set_temperature(self, temp_celsius):
        """
        Sets the temperature on the TC-720 temperature controller.
        
        Args:
            temp_celsius (float): Temperature to set in Celsius (valid range: 0°C to 150°C)
            
        Raises:
            ValueError: If temperature is outside valid range
            RuntimeError: If device is not connected
        """
        # Validate temperature range
        if not (0 <= temp_celsius <= 100):
            raise ValueError(f"Temperature must be between 0°C and 100°C, got {temp_celsius}°C")
            
        bstc = self.convert_temp_to_bstc(temp_celsius)
        cmd_str = ''.join(bstc)
        print(f"[TC720 {self.name}] Setting temperature to {temp_celsius}°C with command: {repr(cmd_str)}")

        if not self.ser or not self.ser.is_open:
            raise RuntimeError("Device is not connected")

        # Write command as a single string
        self.ser.write(cmd_str.encode('ascii'))
        self.ser.flush()
        
        print(f"[TC720 {self.name}] Temperature set command sent successfully!")

    def _build_query(self, cc):  # cc: '01' (INPUT1) or '04' (INPUT2)
        return self.calculate_checksum(['*'] + list(cc) + list('0000') + ['XX', 'XX', '\r'])

    def get_temperature(self, sensor=1):
        cc = '01' if sensor == 1 else '04'
        cmd = self._build_query(cc)
        self.ser.reset_input_buffer()
        
        # Send command as single string
        cmd_str = ''.join(cmd)
        self.ser.write(cmd_str.encode('ascii'))
        self.ser.flush()
        time.sleep(0.05)  # Give device time to respond

        resp = self.ser.read(8)  # expects: * D D D D S S ^
        if len(resp) < 8 or resp[0:1] != b'*':
            raise IOError(f"[TC720] Unexpected response length or format: {resp!r}")

        dddd = resp[1:5].decode('ascii', errors='replace')   # hex value in hundredths °C (signed 16-bit)
        
        # Check if response contains placeholder 'XXXX' (device not ready)
        if 'X' in dddd:
            raise IOError(f"[TC720] Device returned placeholder data: {dddd}")
        
        # optional checksum verify for the 4 data chars:
        expected_checksum = format(sum(ord(c) for c in dddd) & 0xFF, '02x')
        actual_checksum = resp[5:7].decode('ascii', errors='replace')
        if actual_checksum != expected_checksum:
            raise IOError(f"[TC720] Checksum mismatch: expected {expected_checksum}, got {actual_checksum}")

        try:
            val = int(dddd, 16)
        except ValueError as e:
            raise IOError(f"[TC720] Cannot parse temperature hex value '{dddd}': {e}")
            
        if val >= 0x8000:  # handle negatives (two's complement, 16-bit)
            val -= 0x10000
        return val / 100.0  # °C
    
    def close(self):
        """
        Closes the serial connection.
        """
        self.ser.close()
        self._connected = False
        print(f"Disconnected from TC-720 on {self.ser.port}")

    # ---- Status monitoring ---------------------------------------------------
    def status(self) -> dict:
        if not self._connected or not self.ser or not self.ser.is_open:
            return {"ok": False, "code": "disconnected", "msg": "Not connected"}

        try:
            current_temperature = self.get_temperature(sensor=1)
            return {
                "ok": True,
                "code": "ok",
                "msg": f"{current_temperature:.2f}",
                "temperature_c": float(current_temperature),
            }
        except Exception as e:
            return {"ok": False, "code": "no_response", "msg": str(e)}



'''
# ============================== USAGE EXAMPLE ==============================
if __name__ == "__main__":
    controller = TC720(name="TC-720 Temperature Controller", port='COM12', baudrate=230400, timeout=1)
    controller.connect()
    try:
        controller.set_temperature(15)
        #current_temp = controller.read_temperature(sensor=1)   
        #print(f"Current Temperature (Sensor 1): {current_temp:.2f} °C")
        #status = controller.status()
        #print(f"Status: {status}")
    finally:
        controller.stop()
'''