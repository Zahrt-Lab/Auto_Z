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

    def __init__(self, port: str, baudrate: int = 115200, name: str = "Tricontinental_C24000"):
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
        self.uL_per_count = 0.854 # Based on calibration 

    def connect(self) -> None:
        """Connect to the pump via serial port."""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=5.0,        # Read timeout
                write_timeout=5.0   # Write timeout
            )
            
            # Arduino resets on serial connect and sends startup messages
            # Wait for it to finish booting and sending help/params (~3 seconds)
            print(f"{self.name}: Waiting for Arduino to boot...")
            time.sleep(3.0)
            
            # Read and discard all startup messages
            startup_data = b""
            while self.serial.in_waiting:
                startup_data += self.serial.read(self.serial.in_waiting)
                time.sleep(1)  # Small delay to let more data arrive
            
            if startup_data:
                print(f"{self.name}: Cleared {len(startup_data)} bytes of startup data")
            
            self._connected = True
            print(f"{self.name}: Connected on {self.port}")
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.name}: {e}")
        
    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Dispense specified volume at specified flow rate."""
        if not self._connected:
            raise RuntimeError(f"{self.name}: Not connected")
        
        # Clear any pending data in buffer
        if self.serial.in_waiting:
            self.serial.read(self.serial.in_waiting)
        
        # Stop the pump before starting new command
        self.stop()
        print(f"{self.name}: Pump stopped before dispensing")

        # Set the flow rate
        device_rate = self._convert_flow_rate(flow_rate_ul_min)
        cmd_rate = f"output_speed {device_rate}\n"
        print(f"{self.name}: Setting flow rate with command: {cmd_rate.strip()}")
        self.serial.write(cmd_rate.encode())
        self.serial.flush()  # Ensure data is sent
        time.sleep(1)  # Small delay to allow command processing

        # Send the start command (the Arduino expects "start" followed by newline)
        cmd = "start\n"
        print(f"{self.name}: Sending command: {cmd.strip()}")
        self.serial.write(cmd.encode())
        self.serial.flush()  # Ensure data is sent
        time.sleep(1)  # Small delay to allow command processing
        # Wait for and read response (Arduino will echo the command and print status)
        time.sleep(1.0)  # Give Arduino time to process and respond
        response = ""
        timeout_count = 0
        while timeout_count < 10:  # Try for up to 5 seconds
            if self.serial.in_waiting:
                response += self.serial.read(self.serial.in_waiting).decode(errors='ignore')
                if "started" in response.lower() or "pumps started" in response.lower():
                    break
            time.sleep(1)
            timeout_count += 1
        
        print(f"{self.name}: Dispense response: {response.strip()}")
        
        if "ERROR" in response.upper():
            raise RuntimeError(f"{self.name}: Dispense failed - {response}")
        time.sleep(60) #to remove later. THis is just for testing purposes

    def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """For the tricontinental pump, there is no aspirate function."""
        print(f"{self.name}: Aspirate function not implemented for this pump model.")
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
        if not self._connected or not self.serial or not self.serial.is_open:
            return
        
        try:
            cmd = "stop\n"
            self.serial.write(cmd.encode())
            self.serial.flush()
            time.sleep(1)
            # Read any response
            if self.serial.in_waiting:
                self.serial.read(self.serial.in_waiting)
            print(f"{self.name}: Stopped")
        except Exception as e:
            print(f"{self.name}: Error during stop: {e}")

    def status(self) -> str:
        """Return current pump status."""
        if not self._connected:
            return f"{self.name}: Not connected"
        
        try:
            # Clear buffer
            if self.serial.in_waiting:
                self.serial.read(self.serial.in_waiting)
            
            cmd = "status\n"
            self.serial.write(cmd.encode())
            self.serial.flush()
            
            # Wait for response
            time.sleep(1)
            response = ""
            if self.serial.in_waiting:
                response = self.serial.read(self.serial.in_waiting).decode(errors='ignore').strip()
            
            return f"{self.name}: {response}" if response else f"{self.name}: No response"
        except Exception as e:
            return f"{self.name}: Error getting status - {e}"

    def close(self) -> None:
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            try:
                self.stop()  # Ensure pump is stopped
            except Exception:
                pass
            self.serial.close()
            self._connected = False
            print(f"{self.name}: Closed")

    # Helper methods (device-specific)
    def _convert_flow_rate(self, ul_min: float) -> int:
        """Convert µL/min to device-specific rate units."""
        #todo: implement actual conversion based on device specs and calibration
        uL_second = ul_min / 60
        output_speed = uL_second / self.uL_per_count  # Convert to device units
        return int(output_speed)
    
    def _convert_volume(self, ul: float) -> int:
        """Convert µL to device-specific volume units."""
        # todo: implement actual conversion based on device specs and calibration
        device_volume = ul  # Placeholder conversion
        return int(device_volume)