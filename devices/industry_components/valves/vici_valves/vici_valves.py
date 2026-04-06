# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

import serial
import time
from typing import Optional, Union
from ..valves import Valves

class ViciValve(Valves):
    """
    Unified driver for VICI selector valves (6-, 10-, 24-way or any even 2-40 positions).

    The home command is always 'HM', so no special presets are needed.
    """
    VALVES_PRESETS = {
        '6-way':  {'positions': 6},
        '10-way': {'positions': 10},
        '24-way': {'positions': 24},
    }

    def __init__(self, port: str, valve_type: Union[str, int], baudrate: int = 9600, timeout: float = 1):
        # Determines the type of VICI Valve being used
        if isinstance(valve_type, str):
            key = valve_type.lower().replace(' ', '').replace('-', '')
            preset = next((v for k, v in self.VALVES_PRESETS.items()
                           if k.replace('-', '') == key), None)
            if preset is None:
                raise ValueError(f"Unknown valve_type '{valve_type}'")
            self.positions = preset['positions']
        else:
            self.positions = int(valve_type)
            if self.positions % 2 or not (2 <= self.positions <= 40):
                raise ValueError('positions must be an even number between 2 and 40')

        # Serial link
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=timeout
        )

        # Ensure firmware knows the stator size
        self.set_number_of_positions(self.positions)

    def connect(self) -> None:
        """Connect to the valve device."""
        if self.ser and self.ser.is_open:
            return
        self.ser.open()
        print(f"Connected to VICI Valve on {self.ser.port}")

    def send_command(self, command: str) -> str:
        """
        Send a command to the valve and return the response.
        """
        command_str = f"{command}\r"
        self.ser.write(command_str.encode())
        return self.ser.readline().decode().strip()

    def go_to_position(self, pos: int) -> str:
        """Move to absolute position (1-N)."""
        if not 1 <= pos <= self.positions:
            raise ValueError(f"Position must be between 1 and {self.positions}")
        return self.send_command(f"GO{pos:02}")

    def move_home(self) -> str:
        """Moves the actuator to the HOME position."""
        return self.send_command("HM")

    def move_clockwise(self, pos: Optional[int] = None) -> str:
        cmd = f"CW{pos:02}" if pos is not None else "CW"
        return self.send_command(cmd)

    def move_counterclockwise(self, pos: Optional[int] = None) -> str:
        cmd = f"CC{pos:02}" if pos is not None else "CC"
        return self.send_command(cmd)

    def toggle_position(self) -> str:
        """Toggles the actuator to the opposite position (two-position mode only)."""
        return self.send_command("TO")

    def timed_toggle(self) -> str:
        """Toggles, waits preset delay, then returns."""
        return self.send_command("TT")

    def get_position(self) -> str:
        """Returns the current position of the actuator."""
        return self.send_command("CP")

    def set_number_of_positions(self, n: int) -> str:
        """Sets the number of positions (2-40 even)."""
        if n % 2 or not (2 <= n <= 40):
            raise ValueError('Number of positions must be an even number between 2 and 40')
        return self.send_command(f"NP{n:02}")

    def set_delay_time(self, ms: int) -> str:
        """Sets a delay before auto-return (0-65535 ms)."""
        if not (0 <= ms <= 65535):
            raise ValueError('Delay must be 0-65535 ms')
        return self.send_command(f"DT{ms:05}")

    def set_actuator_mode(self, mode: int) -> str:
        """Sets actuator mode (1, 2, or 3)."""
        if mode not in (1, 2, 3):
            raise ValueError('mode must be 1, 2 or 3')
        return self.send_command(f"AM{mode}")

    def learn_stops(self) -> str:
        """Learn physical stops for two-position valve."""
        return self.send_command("LRN")

    def set_device_id(self, new_id: str) -> str:
        """Sets the device ID (single digit or letter)."""
        if len(new_id) != 1 or not (new_id.isdigit() or new_id.isalpha()):
            raise ValueError('device_id must be a single digit (0-9) or letter (A-Z)')
        resp = self.send_command(f"ID{new_id}")
        self.device_id = new_id
        return resp

    def reset_device_id(self) -> str:
        """Resets the device ID to None."""
        resp = self.send_command("*ID*")
        self.device_id = None
        return resp

    def check_firmware_version(self) -> str:
        """Returns the firmware version."""
        return self.send_command("VR")
    
    def status(self) -> str:
        """Returns a string representing the current status of the valve."""
        pos = self.get_position()
        return f"VICI Valve - Position: {pos}"
    
    def stop(self) -> None:
        """Stop any ongoing valve operation promptly and move operations to home."""
        self.move_home()

    def close(self) -> None:
        """Closes the serial connection."""
        self.ser.close()

    def safe_shutdown(self, success: bool) -> None:
        pass


class Multi_VICIValveController:
    """Helper to broadcast the same command to multiple valves."""

    def __init__(self, *valves: ViciValve):
        if not valves:
            raise ValueError('At least one ViciValve required')
        self.valves = valves

    def _broadcast(self, method: str, *args, **kwargs):
        return [getattr(v, method)(*args, **kwargs) for v in self.valves]

    def go_to_position(self, pos: int):
        return self._broadcast('go_to_position', pos)

    def move_home(self):
        return self._broadcast('move_home')

    def move_clockwise(self, pos: Optional[int] = None):
        return self._broadcast('move_clockwise', pos)

    def move_counterclockwise(self, pos: Optional[int] = None):
        return self._broadcast('move_counterclockwise', pos)

    def check_current_position(self):
        return self._broadcast('check_current_position')

    def close(self):
        return self._broadcast('close')