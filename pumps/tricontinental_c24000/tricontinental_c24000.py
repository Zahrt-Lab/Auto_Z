# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Luiz Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

from pumps.pumps import Pump
import serial
import time


class TricontinentalC24000(Pump):
    """Driver for Tricontinental C24000 Dual Syringe Pump."""

    def __init__(self, port: str, baudrate: int = 9600, name: str = "Tricontinental_C24000"):
        """
        Initialize Tricontinental C24000 dual pump.
        
        Args:
            port: Serial port (e.g., 'COM5' or '/dev/ttyUSB0')
            baudrate: Serial baud rate (default 9600)
            name: Friendly name for logging
        """
        self.port = port
        self.baudrate = baudrate
        self.name = name
        self.serial = None
        self._connected = False
        self._pump_a_position = 0  # Track syringe A position
        self._pump_b_position = 0  # Track syringe B position

    def connect(self) -> None:
        """Connect to the pump via serial port."""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=2.0
            )
            time.sleep(0.5)  # Allow hardware to stabilize
            self._connected = True
            print(f"{self.name}: Connected on {self.port}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.name}: {e}")
        
    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Dispense specified volume at specified flow rate."""
        if not self._connected:
            raise RuntimeError(f"{self.name}: Not connected")
        
        # Convert µL/min to device-specific units (example)
        device_rate = self._convert_flow_rate(flow_rate_ul_min)
        device_volume = self._convert_volume(volume_ul)

        # Set the flow rate
        self.set_flow_rate(device_rate)

        # Send hardware-specific command
        # For the tricontinental pump, the command is start"
        
        cmd = f"start\r\n"
        self.serial.write(cmd.encode())
        
        # Wait for completion or response
        # todo: implement proper response handling
        response = self.serial.readline().decode().strip()
        if "ERROR" in response:
            raise RuntimeError(f"{self.name}: Dispense failed - {response}")
        
    def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """For the tricontinental pump, there is no aspirate function."""
        pass

    def set_flow_rate(self, flow_rate_ul_min: float) -> None:
        """Set default flow rate for subsequent operations."""
        if not self._connected:
            raise RuntimeError(f"{self.name}: Not connected")
        
        device_rate = self._convert_flow_rate(flow_rate_ul_min)
        cmd = f"output_speed {device_rate}\r\n"
        self.serial.write(cmd.encode())

    def stop(self) -> None:
        """Stop any ongoing pump operation."""
        if not self._connected:
            return
        
        cmd = "stop\r\n"
        self.serial.write(cmd.encode())
        print(f"{self.name}: Stopped")

    def status(self) -> str:
        """Return current pump status."""
        if not self._connected:
            return f"{self.name}: Not connected"
        
        cmd = "status\r\n"
        self.serial.write(cmd.encode())
        response = self.serial.readline().decode().strip()
        return f"{self.name}: {response}"

    def close(self) -> None:
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            self.stop()  # Ensure pump is stopped
            self.serial.close()
            self._connected = False
            print(f"{self.name}: Closed")

    # Helper methods (device-specific)
    def _convert_flow_rate(self, ul_min: float) -> int:
        """Convert µL/min to device-specific rate units."""
        #todo: implement actual conversion based on device specs and calibration
        output_speed = ul_min  # Placeholder conversion
        return int(output_speed)
    
    def _convert_volume(self, ul: float) -> int:
        """Convert µL to device-specific volume units."""
        # todo: implement actual conversion based on device specs and calibration
        device_volume = ul  # Placeholder conversion
        return int(device_volume)