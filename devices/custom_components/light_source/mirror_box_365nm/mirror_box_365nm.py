# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

import time
import serial

from devices.custom_components.light_source.light_source_base import PhotoReactor


class MirrorBox365nm(PhotoReactor):
    """
    Serial wrapper for the custom Arduino-based mirror box 365nm light source.

    Arduino commands (newline-terminated):
      s           -> prints 2 lines (relay states + tab-separated temps), no OK
      dim <0-255> -> sets dimmer (0=brightest, 255=off), replies OK

    Arduino streams TC3,TC4 temperatures as "t3,t4" CSV every 1 second.
    TC1 and TC2 are nonfunctional hardware and are not used.
    """

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.name = "MirrorBox365nm"
        self.ser = None

    def connect(self):
        self.ser = serial.Serial(self.port, baudrate=self.baudrate, timeout=self.timeout)
        time.sleep(2.0)  # Wait for Arduino reset
        self.drain(1.0)  # Clear startup messages

    def close(self):
        try:
            if self.ser:
                self.ser.close()
        finally:
            self.ser = None

    def drain(self, seconds: float = 0.5) -> None:
        """Clear the serial input buffer by reading all available bytes."""
        end = time.time() + seconds
        while time.time() < end:
            time.sleep(0.05)
            if self.ser.in_waiting > 0:
                try:
                    self.ser.read(self.ser.in_waiting)
                except Exception:
                    pass
        # Final sweep
        if self.ser.in_waiting > 0:
            try:
                self.ser.read(self.ser.in_waiting)
            except Exception:
                pass

    def _read_response(self, max_lines: int = 10) -> str:
        """Read the next non-CSV response line, skipping temperature stream lines.
        Uses self.ser.timeout per readline — never subdivides it."""
        deadline = time.time() + (self.timeout * max_lines)
        for _ in range(max_lines):
            if time.time() >= deadline:
                break
            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                continue
            if line.count(',') == 1:
                try:
                    [float(p) for p in line.split(',')]
                    continue  # temperature stream line — skip
                except ValueError:
                    pass
            return line
        return ""

    # --- Public API ---

    def set_dimmer(self, dimmer_value: int) -> str:
        """Set dimmer (0=brightest, 255=off). Value is clamped to 0–255."""
        dimmer_value = max(0, min(255, dimmer_value))
        self.ser.write(f"dim {dimmer_value}\n".encode('utf-8'))
        return self._read_response()
    
    # TODO: I want to work on a cleaner way to return data from the status() alongside other approaches
    # This will due for now but future I want to standardize this across all instruments
    def status(self) -> dict:
        """Request status from Arduino.

        Returns:
            dict with keys: light1_on, light2_on, dimmer_pwm,
                            temp_light1_c (TC3), temp_light2_c (TC4),
                            raw_line1, raw_line2
        """
        self.drain(0.3)          # Clear accumulated stream lines before requesting status
        self.ser.write(b"s\n")
        line1 = self._read_response()
        line2 = self._read_response()

        # Parse line1: "Light1: ON | Light2: OFF | DimmerPWM: 128"
        light1_on = None
        light2_on = None
        dimmer_pwm = None
        try:
            for segment in line1.split(" | "):
                if segment.startswith("Light1"):
                    light1_on = "ON" in segment
                elif segment.startswith("Light2"):
                    light2_on = "ON" in segment
                elif segment.startswith("DimmerPWM"):
                    dimmer_pwm = int(segment.split(":")[1].strip())
        except Exception:
            pass

        # Parse line2: "Temps(C): 45.30\t44.80"
        temp_light1_c = None
        temp_light2_c = None
        try:
            parts = line2.replace("Temps(C):", "").strip().split('\t')
            temp_light1_c = float(parts[0])
            temp_light2_c = float(parts[1])
        except Exception:
            pass

        return {
            'light1_on': light1_on,
            'light2_on': light2_on,
            'dimmer_pwm': dimmer_pwm,
            'temp_light1_c': temp_light1_c,
            'temp_light2_c': temp_light2_c,
            'raw_line1': line1,
            'raw_line2': line2,
        }

    def read_temperature_stream(self, timeout: float = 2.0) -> dict:
        """Read one temperature CSV line from the Arduino stream.

        Returns:
            dict with temp_light1_c (TC3) and temp_light2_c (TC4),
            or {'error': ..., 'raw': ''} if no valid data found.
        """
        original_timeout = self.ser.timeout
        self.ser.timeout = timeout
        try:
            for _ in range(10):
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                if not line or ',' not in line:
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) == 2:
                    try:
                        t3, t4 = float(parts[0]), float(parts[1])
                        return {'temp_light1_c': t3, 'temp_light2_c': t4, 'raw': line}
                    except ValueError:
                        continue
            return {'error': 'No valid temperature data found in stream', 'raw': ''}
        finally:
            self.ser.timeout = original_timeout
