# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

'''
Commands to control the DH2000 light source via Arduino TTL controller.
- Enables calibration to be performed between experimental runs.
- Allows us to turn on and off lamps to extend their lifetimes if any failures occur during the experiment. 
'''

import serial
import time
import threading

from devices.industry_components.uv_detectors.uv_detector_light_source_base import uv_detector_light_source_base

class DH2000LightSource(uv_detector_light_source_base):
    """
    Wraps the Arduino DH-2000 TTL controller.

    Arduino commands:
      o/c/d/h -> prints OK
      s       -> prints 3 lines, no OK
    """
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0,
                 retries: int = 10, boot_delay_s: float = 2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.retries = retries
        self.boot_delay_s = boot_delay_s
        self.name = "DH2000"


        self.ser = None
        self.control_file_path: str = None  # Set by GeneralExperimentMethod after construction

        # TODO: A coarser lock like this prevents races between the StatusMonitor thread and
        # main-thread commands, but a smarter approach would be a dedicated serial I/O thread
        # with a command queue so status polling and commands can be properly prioritized
        # rather than one blocking the other entirely.
        self._lock = threading.RLock()

    # --- lifecycle ---
    def connect(self):
        self.ser = serial.Serial(self.port, baudrate=self.baudrate, timeout=self.timeout)
        time.sleep(self.boot_delay_s)
        self._drain(seconds=3.0)  # Give Arduino time to send startup messages and clear buffer

    def close(self):
        try:
            if self.ser:
                self.ser.close()
        finally:
            self.ser = None

    # --- internal IO ---
    def _drain(self, seconds: float = 1.0) -> None:
        """Aggressively drain the serial buffer to clear any stale/corrupted data."""
        if not self.ser:
            return
        end = time.time() + seconds
        # Keep draining until time expires
        while time.time() < end:
            time.sleep(0.05)  # Small delay to let data accumulate
            if self.ser.in_waiting > 0:
                try:
                    # Read all available bytes at once
                    self.ser.read(self.ser.in_waiting)
                except Exception:
                    pass
        
        # Final check to ensure buffer is completely empty
        time.sleep(0.1)
        if self.ser.in_waiting > 0:
            try:
                self.ser.read(self.ser.in_waiting)
            except Exception:
                pass

    def _readline_str(self) -> str:
        raw = self.ser.readline() if self.ser else b""
        if not raw:
            return ""
        return raw.decode("utf-8", errors="ignore").strip()

    def dh2000_command(self, command: str, expect_ok: bool = True) -> None:
        if not self.ser:
            raise RuntimeError("DH2000 serial not connected")
        if not isinstance(command, str) or len(command) != 1:
            raise ValueError("Command must be a single character")
        if command not in ['o', 'c', 'h', 'd', 's', 'x']:
            raise ValueError("Invalid command character")

        with self._lock:
            # Clear buffer before sending command
            self._drain(seconds=0.5)

            # Small pause after drain for stability
            time.sleep(0.05)

            # Send just the character without newline - Arduino reads single chars
            self.ser.write(command.encode("ascii", errors="ignore"))
            self.ser.flush()

            # Give Arduino time to process and respond
            time.sleep(0.2)

            if not expect_ok:
                return

            deadline = time.time() + (self.timeout or 2.0)
            received_lines = []
            received_text = ""

            # Keep reading until we find OK or timeout
            while time.time() < deadline:
                line = self._readline_str()
                if line:
                    received_lines.append(line)
                    received_text += line.upper()
                    # Look for OK anywhere in any received text (very lenient)
                    if "OK" in received_text:
                        return

            raise RuntimeError(f"Timed out waiting for OK after '{command}' command. Received: {received_lines}")

    # --- public control ---
    def shutter_open(self):   self.dh2000_command("o", expect_ok=True)
    def shutter_close(self):  self.dh2000_command("c", expect_ok=True)
    def halogen_toggle(self): self.dh2000_command("h", expect_ok=True)
    def deuterium_toggle(self): self.dh2000_command("d", expect_ok=True)

    def status(self) -> dict:
        """
        Returns dict:
          {'shutter_open': bool|None, 'halogen_on': bool|None, 'deuterium_on': bool|None, 'raw': [lines]}
        """
        with self._lock:
            self.dh2000_command("s", expect_ok=False)
            dh2000_components_status = []
            timeout = time.time() + (self.timeout or 2.0)
            while time.time() < timeout and len(dh2000_components_status) < 3:
                dh2000_component_status = self._readline_str()
                if dh2000_component_status:
                    dh2000_components_status.append(dh2000_component_status)

        def _parse_bool(dh2000_component_status: str, key: str):
            if key.lower() in dh2000_component_status.lower():
                if "OPEN" in dh2000_component_status.upper() or "ON" in dh2000_component_status.upper():
                    return True
                if "CLOSED" in dh2000_component_status.upper() or "OFF" in dh2000_component_status.upper():
                    return False
            return None

        shutter = None
        hal = None
        deut = None
        for dh2000_component_status in dh2000_components_status:
            if shutter is None:
                shutter = _parse_bool(dh2000_component_status, "Shutter")
            if hal is None:
                hal = _parse_bool(dh2000_component_status, "Halogen")
            if deut is None:
                deut = _parse_bool(dh2000_component_status, "Deuterium")

        return {"shutter_open": shutter, "halogen_on": hal, "deuterium_on": deut, "arduino_output": dh2000_components_status}

    def safe_shutdown(self, success: bool) -> None:
        """
        success=True  → leave DH2000 state unchanged (lights stay as-is).
        success=False → check control_file_path:
            True  (or unset) → skip shutdown (leave lights on).
            False            → close shutter + both lamps OFF.
        Retries up to self.retries; caller should catch and continue.
        """
        if success:
            return

        # Check whether the operator wants us to skip shutdown (e.g. keep lights on after failure)
        if self.control_file_path:
            try:
                with open(self.control_file_path, 'r') as f:
                    skip = f.read().strip().lower() == "true"
                if skip:
                    return
            except Exception:
                pass  # If we can't read the file, proceed with shutdown

        last_error = None
        for _ in range(self.retries):
            try:
                status = self.status()
                if status["halogen_on"] is None or status["deuterium_on"] is None or status["shutter_open"] is None:
                    raise RuntimeError(f"Unparseable status: {status['arduino_output']}")

                # close shutter first (your spec)
                if status["shutter_open"]:
                    self.shutter_close()

                # then lamps OFF
                status2 = self.status()
                if status2["halogen_on"]:
                    self.halogen_toggle()
                if status2["deuterium_on"]:
                    self.deuterium_toggle()

                # verify
                status3 = self.status()
                if (status3["shutter_open"] is False) and (status3["halogen_on"] is False) and (status3["deuterium_on"] is False):
                    return
                raise RuntimeError(f"Did not reach OFF state. status={status3}")
            except Exception as e:
                last_error = e
                time.sleep(0.25)
        raise RuntimeError(f"safe_shutdown failed after {self.retries} attempts: {last_error}")
    
'''
light = DH2000LightSource(port='COM27')
light.connect()
light.deuterium_toggle()
light.halogen_toggle()
time.sleep(10.0)
light.shutter_open()
time.sleep(10.0)
light.shutter_close()
light.safe_shutdown()
light.close()
'''