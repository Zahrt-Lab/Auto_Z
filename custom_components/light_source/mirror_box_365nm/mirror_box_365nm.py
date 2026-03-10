# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

import time
import serial

class MirrorBox365nm:
    """
    Serial python wrapper for the custom Arduino-based mirror box 365nm light source

    Arduino commands:
     s           -> prints 4 lines of temperatures (peltiers cold side, peltiers hot side, light 1, light 2), no OK
     off         -> turns off the light sources
     dim <0-255> -> sets the dimmer value for the light sources, where 0 is full brightness and 255 is dimmest.   
    
    Arduino also streams:
        TEMP_COLD, TEMP_HOT, TEMP_LIGHT1, TEMP_LIGHT2 as CSV lines every 5 seconds.
    """

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.name = "MirrorBox365nm"

        self.ser = None

    def connect(self):
        self.ser = serial.Serial(self.port, baudrate=self.baudrate, timeout=self.timeout)
        time.sleep(2.0)  # Give Arduino time to reset and start up
        self.drain(1.0)  # Clear any startup messages

    def close(self):
        try:
            if self.ser:
                self.ser.close()
        finally:
            self.ser = None

    def drain(self, wait_time: float = 0.5) -> None:
        """Clear the serial input buffer by reading all available data."""
        time.sleep(wait_time)
        while self.ser.in_waiting > 0:
            try:
                self.ser.readline()
            except Exception:
                break
    
    def _read_response(self, timeout: float = 1.0, max_lines: int = 5) -> str:
        """Read a response, filtering out temperature CSV lines.
        Returns the first non-CSV line (like OK, ERR, or status info)."""
        original_timeout = self.ser.timeout
        self.ser.timeout = timeout / max_lines
        try:
            for _ in range(max_lines):
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                # Check if it's a temperature CSV line (4 comma-separated floats)
                if line.count(',') == 3:
                    try:
                        # Try to parse as floats - if successful, it's temperature data
                        parts = line.split(',')
                        [float(p) for p in parts]
                        continue  # Skip temperature lines
                    except ValueError:
                        pass  # Not temperature data, return it
                return line
            return ""  # No non-temperature response found
        finally:
            self.ser.timeout = original_timeout

    # Public API
    def turn_off(self) -> None:
        """Turn off the light sources."""
        self.ser.write("off\n".encode("utf-8"))
        # Read the OK response (filtering out temperature data)
        response = self._read_response()
        return response

    def set_dimmer(self, dimmer_value: int) -> str:
        """Set the dimmer value for the light sources (0=brightest, 255=dimmest)."""
        # Clamp to valid range (don't raise error, just clamp like Arduino does)
        dimmer_value = max(0, min(255, dimmer_value))
        self.ser.write(f"dim {dimmer_value}\n".encode('utf-8'))
        # Read the OK response (filtering out temperature data)
        response = self._read_response()
        return response

    def status(self) -> dict:
        """Request a status update from the Arduino, which will print temperatures and status of devices."""
        self.ser.write(b"s\n")
        # Arduino prints 4 lines for status command
        temperatures = []
        for _ in range(4):
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                temperatures.append(line)
        return {'status_lines': temperatures, 'raw': '\n'.join(temperatures)}
    
    def read_temperature_stream(self, timeout: float = 2.0) -> dict:
        """Read one line of CSV temperature data from the Arduino stream.
        Returns dict with temp_cold, temp_hot, temp_light1, temp_light2."""
        original_timeout = self.ser.timeout
        self.ser.timeout = timeout
        try:
            # Read lines until we get valid CSV temperature data
            for _ in range(10):  # Try up to 10 lines
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                # Check if line contains comma-separated values
                if ',' in line or '\t' in line:
                    # Try comma-separated first
                    separator = ',' if ',' in line else '\t'
                    temperatures = [p.strip() for p in line.split(separator)]
                    
                    if len(temperatures) == 4:
                        try:
                            temps = [float(temperature) for temperature in temperatures]
                            return {
                                'temp_cold': temps[0],
                                'temp_hot': temps[1],
                                'temp_light1': temps[2],
                                'temp_light2': temps[3],
                                'raw': line
                            }
                        except ValueError:
                            # Not valid floats, continue
                            continue
            
            return {'error': 'No valid temperature data found in stream', 'raw': ''}
        
        finally:
            self.ser.timeout = original_timeout

