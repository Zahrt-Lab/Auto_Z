# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Luiz Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

from pumps.pumps import Pump
from pumps.tricontinental_c24000 import tricont_pyserial as tri
import time

'''
The purpose of this code is to control the Tricontinental C24000 dual syringe pump 
via its serial interface.
'''


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
    # TODO: Should make the calibration function necessary in the pumps.py 
    # but that can be in a future develops version, not urgent
    '''Calibration values for 25mL syringe, 0.06376 µL/count (1 / 15.6835 counts/µL)
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
    '''
    # Calibration values for 1mL syringe, 0.005107 µL/count (1 / 196.82 counts/µL)
    # Is this even needed? The pumps have the same calibration value across all flow rates
    CALIBRATION_VALUES = {
        # flow_rate_ul_min: counts_per_uL
        100: 196.82,      # Example calibration at 100 µL/min
        200: 196.82,      # Example calibration at 200 µL/min
        500: 196.82,      # Example calibration at 500 µL/min
        1000: 196.82,     # Example calibration at 1000 µL/min
        1500: 196.82,     # Example calibration at 1500 µL/min
        2000: 196.82,     # Example calibration at 2000 µL/min
    }
    DEFAULT_COUNTS_PER_UL = 196.82  # Default if flow rate not in calibration table (1 / 0.005107)

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
        
        # Calibration parameters
        self.uL_per_count = 0.005107  # Based on calibration (µL dispensed per count)
        self.counts_per_uL = 1 / self.uL_per_count  
        
        # Current operation state
        self.flow_rate_ul_min = 0.0
        self.flow_rate_ul_sec = 0.0 

    def connect(self) -> None:
        """Connect to the pump via serial port."""
        try:
            self.serial = tri.connect(port=self.port, baudrate=self.baudrate)
            
            time.sleep(2)  # Wait for pump to initialize
            
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
        
        # Check initialization status
        print(f"{self.name}: Checking pump initialization status...")
        is_A_initialized = tri.is_initialized(self.serial, pump="A")
        is_B_initialized = tri.is_initialized(self.serial, pump="B")
        
        if is_A_initialized is None or is_B_initialized is None:
            raise RuntimeError(f"{self.name}: Failed to get initialization status. Are the pumps connected?")
        
        if is_A_initialized:
            print(f"{self.name}: Pump A is already initialized.")
        else:
            print(f"{self.name}: Pump A is not initialized.")
            print(f"{self.name}: Initializing Pump A...")
            tri.initialize_pump(self.serial, pump="A")        
        if is_B_initialized:
            print(f"{self.name}: Pump B is already initialized.")
        else:
            print(f"{self.name}: Pump B is not initialized.")
            print(f"{self.name}: Initializing Pump B...")
            tri.initialize_pump(self.serial, pump="B")

        tri.check_until_initialized(self.serial, pump="A")
        tri.check_until_initialized(self.serial, pump="B")
        print(f"{self.name}: Both pumps initialized successfully.")
        
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
        dispense_speed = self._convert_flow_rate(flow_rate_ul_min)
        continuous_flow_cmd_A = tri.compose_command_continuous_flow_A(dispense_speed=dispense_speed)
        continuous_flow_cmd_B = tri.compose_command_continuous_flow_B(dispense_speed=dispense_speed)
        
        #Run continuos flow on both pumps
        tri.run_continuous_flow(self.serial,pump="A", command=continuous_flow_cmd_A)
        tri.run_continuous_flow(self.serial,pump="B", command=continuous_flow_cmd_B)
        
        time.sleep(1)  # Give time for the valves to change position
        is_output_valve_A = tri.is_valve_output(self.serial, pump="A")
        is_output_valve_B = tri.is_valve_output(self.serial, pump="B")        

        while (not is_output_valve_A) and (not is_output_valve_B):
            print(f"{self.name}: Waiting for pumps to start dispensing...")
            time.sleep(0.5)
            is_output_valve_A = tri.is_valve_output(self.serial, pump="A")
            time.sleep(0.5)
            is_output_valve_B = tri.is_valve_output(self.serial, pump="B")

        start_time = time.time()

        while time.time() - start_time < pump_time_sec:
            elapsed = time.time() - start_time
            print(f"{self.name}: Pumping... {elapsed:.2f}/{pump_time_sec:.2f} s elapsed")
            time.sleep(60)  # Update every 60 seconds

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

        self.flow_rate_ul_min = abs(flow_rate_ul_min)
        device_rate = self._convert_flow_rate(flow_rate_ul_min)
        cmd = f"output_speed {device_rate}\r\n"
        self.serial.write(cmd.encode())

    def stop(self) -> None:
        """Stop any ongoing pump operation."""
        if not self._connected or not self.serial or not self.serial.is_open:
            return
        
        try:
            tri.stop_pump(self.serial, pump="A")
            print(f"{self.name}: Stopped pump A")
            time.sleep(0.5)  # Small delay between stops
            tri.stop_pump(self.serial, pump="B")
            print(f"{self.name}: Stopped pump B")
            time.sleep(0.5)  # Allow time for pump to stop
        except Exception as e:
            print(f"{self.name}: Error during stop: {e}")

    def status(self) -> str:
        """Return current pump status."""
        if not self._connected:
            return f"{self.name}: Not connected"
        
        try:
            response_A = tri.check_status(self.serial, pump="A")
            response_B = tri.check_status(self.serial, pump="B") 
            return f"{self.name}: Pump A status: {response_A}, Pump B status: {response_B}"
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
        """Calculate the pump time in seconds based on volume and flow rate.
        
        Uses the formula: time = volume / (flow_rate / 60)
        Similar to VICI M6 approach.
        
        Parameters:
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
