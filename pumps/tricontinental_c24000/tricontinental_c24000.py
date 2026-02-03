# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Luiz Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

from pyparsing import line
from pyparsing import line
from pumps.pumps import Pump
import serial
import time


class TricontinentalC24000(Pump):
    """Driver for Tricontinental C24000 Dual Syringe Pump.
    
    Uses a VICI-style approach for volume control:
    - Converts flow rate and volume to device-specific units
    - Calculates pump time based on volume and flow rate
    - Blocks until the calculated time has elapsed
    - Stops the pump after completion
    """

    # Calibration values: maps flow_rate (µL/min) to counts_per_uL
    # TODO: Populate with actual calibration data for your specific pump
    CALIBRATION_VALUES = {
        # flow_rate_ul_min: counts_per_uL
        100: 15.6835,      # Example calibration at 100 µL/min
        200: 15.6835,      # Example calibration at 200 µL/min
        500: 15.6835,      # Example calibration at 500 µL/min
        1000: 15.6835,     # Example calibration at 1000 µL/min
        1500: 15.6835,     # Example calibration at 1500 µL/min
        2000: 15.6835,     # Example calibration at 2000 µL/min
    }
    DEFAULT_COUNTS_PER_UL = 15.6835  # Default if flow rate not in calibration table (1 / 0.10675)

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
        
        # Calibration parameters
        self.uL_per_count = 0.06376  # Based on calibration (µL dispensed per count)
        self.counts_per_uL = 1 / self.uL_per_count  
        
        # Current operation state
        self.flow_rate_ul_min = 0.0
        self.flow_rate_ul_sec = 0.0 

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
                time.sleep(2)  # Small delay to let more data arrive
            
            if startup_data:
                print(f"{self.name}: Cleared {len(startup_data)} bytes of startup data")
            
            self._connected = True
            print(f"{self.name}: Connected on {self.port}")
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.name}: {e}")
        
        init_status_cmd = "init_status\n"
        self.serial.write(init_status_cmd.encode())
        time.sleep(5)  # Wait for response
        response = ""
        if self.serial.in_waiting:
            response = self.serial.read(self.serial.in_waiting).decode(errors='ignore').strip()
        # parse "INIT_STATUS A=1 B=0"
        parts = dict(item.split("=") for item in response.split() if "=" in item)
        a = int(parts["A"])
        b = int(parts["B"])
        print(f"{self.name}: Initialization status - Pump A: {a}, Pump B: {b}")

        # Initialize pumps if not already initialized
        if a == 0 or b == 0:
            print(f"{self.name}: Pumps not initialized. Initializing pumps...")
            initialization_cmd = "initialize \n"
            self.serial.write(initialization_cmd.encode())
            # Listen to response, but not time based, wait for arduino response
            time.sleep(10)
            response = ""
            if self.serial.in_waiting:
                response = self.serial.read(self.serial.in_waiting).decode(errors='ignore').strip()
            print(f"{self.name}: Initialization command response: {response}")
            if "INIT_STATUS_ERROR" in response.upper():
                raise RuntimeError(f"{self.name}: Initialization failed - {response}")
            elif "INIT_DONE" in response:
                # TODO : 40 seconds is quite long, is it necessary to wait this long
                time.sleep(40)  # ensure pumps are ready after init
                print(f"{self.name}: Initialization completed successfully.")
                print(f"{self.name}: Refilling pump B with initial refill...")
                fill_b_cmd = "fill_B\n"
                self.serial.write(fill_b_cmd.encode())
                # TODO : 40 seconds is quite long, is it necessary to wait this long
                time.sleep(40)  # Wait for the refill command to complete
                response = ""
                if self.serial.in_waiting:
                    response = self.serial.read(self.serial.in_waiting).decode(errors='ignore').strip()
                print(f"{self.name}: Fill B command response: {response}")
                
                if "ERROR" in response.upper():
                    raise RuntimeError(f"{self.name}: Fill B failed - {response}")
                
                else:
                    # TODO : 40 seconds is quite long, is it necessary to wait this long
                    time.sleep(40)  # Wait for the refill command to complete
                    print(f"{self.name}: Pump B filled with initial refill successfully.")
                
            else:
                print(f"{self.name}: Unexpected initialization response: {response}")
            
        elif a == 1 and b == 1:
            print(f"{self.name}: Pumps already initialized.")

        else:
            print(f"{self.name}: Unknown initialization status: {response}")

        
    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Dispense specified volume at specified flow rate.
        
        Uses VICI-style approach:
        1. Calculate the pump time based on volume and flow rate
        2. Set the flow rate on the device
        3. Start pumping
        4. Wait for the calculated time + buffer
        5. Stop the pump
        
        Args:
            flow_rate_ul_min: Flow rate in µL/min
            volume_ul: Volume to dispense in µL
        """
        if not self._connected:
            raise RuntimeError(f"{self.name}: Not connected")
        
        if flow_rate_ul_min <= 0:
            raise ValueError(f"{self.name}: Flow rate must be > 0, got {flow_rate_ul_min}")
        if volume_ul <= 0:
            raise ValueError(f"{self.name}: Volume must be > 0, got {volume_ul}")
        
        # Store current flow rate
        self.flow_rate_ul_min = abs(flow_rate_ul_min)
        # TODO : Does self.flow_rate_ul_sec be set to abs() if self.flow_rate_ul_min is set to absolute?
        self.flow_rate_ul_sec = self.flow_rate_ul_min / 60.0
        
        # Get calibration value for this flow rate (or use default)
        self.counts_per_uL = self.CALIBRATION_VALUES.get(
            self.flow_rate_ul_min, 
            self.DEFAULT_COUNTS_PER_UL
        )
        
        # Calculate pump time using helper function
        pump_time_sec, total_wait_time = self._calculate_pump_time(volume_ul, self.flow_rate_ul_min)
        
        print(f"{self.name}: Dispensing {volume_ul} µL at {flow_rate_ul_min} µL/min")
        print(f"{self.name}: Calculated pump time: {pump_time_sec:.2f} s (total wait: {total_wait_time:.2f} s)")
        
        # Clear any pending data in buffer
        if self.serial.in_waiting:
            self.serial.read(self.serial.in_waiting)
        
        # Stop the pump before starting new command
        self.stop()
        print(f"{self.name}: Pump stopped before dispensing")
        self.serial.flush()
        time.sleep(2)  # Small delay to ensure pump is stopped

        # Set the flow rate
        device_rate = self._convert_flow_rate(flow_rate_ul_min)
        cmd_rate = f"output_speed {device_rate}\n"
        print(f"{self.name}: Setting flow rate with command: {cmd_rate.strip()}")
        self.serial.write(cmd_rate.encode())
        self.serial.flush()
        time.sleep(2)  # Small delay to allow command processing

        # Send the start command
        cmd = "start\n"
        print(f"{self.name}: Sending command: {cmd.strip()}")
        self.serial.write(cmd.encode())
        self.serial.flush()
        time.sleep(2)  # Small delay to allow command processing
        
        # Wait for confirmation that pump started
        response = ""
        timeout_count = 0
        while timeout_count < 5:  # Try for up to 2.5 seconds
            if self.serial.in_waiting:
                response += self.serial.read(self.serial.in_waiting).decode(errors='ignore')
                if "started" in response.lower() or "pumps started" in response.lower():
                    break
            time.sleep(2)
            timeout_count += 1
        
        print(f"{self.name}: Dispense response: {response.strip()}")
        
        if "ERROR" in response.upper():
            raise RuntimeError(f"{self.name}: Dispense failed - {response}")
        
        # Wait for the calculated pump time
        print(f"{self.name}: Waiting {total_wait_time:.2f} s for dispense to complete...")
        time.sleep(total_wait_time)
        
        # Stop the pump after dispensing
        self.stop()
        print(f"{self.name}: Dispense complete - {volume_ul} µL dispensed")

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
            time.sleep(2)
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
        """Convert µL/min to device-specific rate units (counts/second).
        
        The device expects a speed in counts per second.
        Formula: output_speed = (µL/sec) / (µL/count) = (µL/sec) * (counts/µL)
        
        Args:
            ul_min: Flow rate in µL/min
            
        Returns:
            Device speed in counts/second
        """
        # Get calibration value for this flow rate (or use default)
        counts_per_uL = self.CALIBRATION_VALUES.get(
            abs(ul_min), 
            self.DEFAULT_COUNTS_PER_UL
        )
        
        uL_per_second = abs(ul_min) / 60.0
        # TODO : Does the manual call it output_speed, is their a more descriptive name to give this variable?
        output_speed = uL_per_second * counts_per_uL  # counts/second
        
        return int(output_speed)
    
    def _convert_volume_to_counts(self, volume_ul: float) -> int:
        """Convert µL to device-specific volume units (counts).
        
        Args:
            volume_ul: Volume in µL
            
        Returns:
            Volume in device counts
        """
        # TODO : Is there a more descriptive name we can use besides total_counts for this part
        total_counts = abs(volume_ul) * self.counts_per_uL
        return int(total_counts)
    
    def _calculate_pump_time(self, volume_ul: float, flow_rate_ul_min: float, buffer_sec: float = 2.0) -> tuple:
        """Calculate the pump time based on volume and flow rate.
        
        Uses the formula: time = volume / (flow_rate / 60)
        Similar to VICI M6 approach.
        
        Args:
            volume_ul: Volume to pump in µL
            flow_rate_ul_min: Flow rate in µL/min
            buffer_sec: Safety buffer time in seconds (default 2.0)
            
        Returns:
            Tuple of (pump_time_sec, total_wait_time) where:
                - pump_time_sec: Raw calculated pump time in seconds
                - total_wait_time: pump_time_sec + buffer_sec
        """
        if flow_rate_ul_min <= 0:
            raise ValueError("Flow rate must be > 0")
        if volume_ul <= 0:
            raise ValueError("Volume must be > 0")
        
        flow_rate_ul_sec = abs(flow_rate_ul_min) / 60.0
        pump_time_sec = abs(volume_ul) / flow_rate_ul_sec
        total_wait_time = pump_time_sec + buffer_sec
        
        return pump_time_sec, total_wait_time
    
    def get_pump_parameters(self) -> None:
        """Print current pump parameters (similar to VICI M6)."""
        print(f"Pump parameters for {self.name}:")
        print(f"  Flow rate: {self.flow_rate_ul_min} µL/min ({self.flow_rate_ul_sec:.4f} µL/sec)")
        print(f"  µL per count: {self.uL_per_count}")
        print(f"  Counts per µL: {self.counts_per_uL:.4f}")
        print(f"  Connected: {self._connected}")
        print(f"  Port: {self.port} @ {self.baudrate} baud")
