# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and David Polefrone are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

from __future__ import annotations

import time
import serial
from devices.industry_components.pumps.pumps import Pump

# TODO : Need to add a max flow rate volume of 5 mL/min which is max 
# recommended flow rate for the pump. 
# TODO: Once test

class VICI_M6_Pumps(Pump):

    def __init__(self, port: str = 'COM16', baud_rate: int = 9600, timeout: int = 1) -> None:

        try:
            self.ser: serial.Serial | None = serial.Serial(port, baud_rate, timeout=timeout)
            print(f"Successfully initialized serial connection with VICI M6 pump.")
        except serial.SerialException as e:
            print(f"Failed to initialize serial connection with VICI M6 pump: {e}")
            self.ser = None
        self.direction = "aspirating"
        self.direction_multiplier = -1  # Default to aspirating
        self._initialize_parameters()

    def _initialize_parameters(self) -> None:
        """Initialize all pump parameters and math constants."""
        # Communication and motor control parameters
        self.MS = 256  # Microsteps per step
        self.P = 0  # Motor position
        self.VI = 1000  # Initial velocity (steps/sec)
        self.VM = 76800  # Maximum velocity (steps/sec)
        self.A = 1000000  # Acceleration (steps/sec^2)
        self.D = 1000000  # Deceleration (steps/sec^2)
        self.MA = None  # Absolute movement (steps/sec)
        self.MR = None  # Relative movement (step/sec)
        self.SL = None  # Speed override (steps/sec)
        self.SL_units = "steps/sec"

        # Math and volume calculations
        self.volume = 1000  # Total volume (uL)
        self.volume_units = "uL"
        self.flow_rate_min = 100  # Default flow rate (uL/min)
        self.flow_rate_sec = self.flow_rate_min / 60  # Convert to uL/sec
        self.flow_rate_units_min = "uL/min"
        self.flow_rate_units_sec = "uL/sec"

        # Motor and pump specifics
        self.micro_steps = 256
        self.motor_steps = 200
        self.gearbox_ratio = 9.87
        self.micro_steps_per_rev = self.micro_steps * self.motor_steps * self.gearbox_ratio
        self.pump_head_volume = 99.771  # Pump head volume (uL/rev)
        self.steps_per_ul = self.micro_steps_per_rev / self.pump_head_volume  # Steps per uL
        self.steps_per_ul_units = "steps/uL"

        self._stop_flag = False

    def set_flow_rate(self, flow_rate_min: float, direction: str) -> None:
        try:
            if flow_rate_min is None or isinstance(flow_rate_min, str):
                raise ValueError(f"flow_rate_min must be a numeric value, got {type(flow_rate_min).__name__}")
            self.flow_rate_min = float(flow_rate_min)
            self.flow_rate_sec = self.flow_rate_min / 60.0

            if self.flow_rate_min > 5000:
                raise ValueError(f"Flow rate {self.flow_rate_min} uL/min exceeds the maximum of 5000 uL/min for the VICI M6 pump.")

            if direction not in ["aspirating", "dispensing"]:
                raise ValueError(f"Invalid direction '{direction}'. Must be 'aspirating' or 'dispensing'.")

            self.direction = direction
            self.direction_multiplier = 1 if direction == "dispensing" else -1
            # TODO : Implement a more comprehensive calibration system
            calibration_values = {
                "dispensing": {
                    1000: 2494.720, 1500: 2584.774, 200: 2426.062, 2000: 2440.881, 41.33: 2426.062
                },
                "aspirating": {
                    1000: 2606.371104, 1500: 3166.612, 200: 2451.378376, 2000: 2955.059, 41.33: 2451.378376
                }
            }

            self.steps_per_ul = calibration_values[self.direction].get(self.flow_rate_min)
            if not self.steps_per_ul:
                print(f"No calibration data for flow rate {self.flow_rate_min} uL/min in {self.direction} mode.")
                self.steps_per_ul = 2606.371104

            self.VM = abs(int(self.steps_per_ul * self.flow_rate_sec))

            print(f"{direction.capitalize()} at {self.flow_rate_min} uL/min")
            print(f"Steps per uL: {self.steps_per_ul}, VM: {self.VM} steps/sec")

        except ValueError:
            raise

    # Initiates the pump
    def start(self) -> None:
        # Initiates serial connection
        try:
            if not self.ser.is_open:
                self.ser.open()
                print('Serial connection opened.')
                self.reset_parameters()
        except Exception as e:
            print(f'Error opening serial connection: {e}')

    def connect(self) -> None:
        """Compatibility wrapper to match the Pump abstract interface."""
        self.start()

    def send_command(self, command: str) -> None:
        if not self.ser or not self.ser.is_open:
            print("Serial connection for VICI M6 Pumps is not open.")
            return
        """Send a command to the pump and wait for a response"""
        print(f"Command {command}")
        self.ser.write((command + '\r').encode())
        time.sleep(0.1)
        response = self.ser.read(self.ser.in_waiting)
        print(f"Command sent to the pump \"{response.decode()}\"")

    def get_pump_parameters(self) -> str:
        result = ("Pump parameters:\n"
                  f"The flow rate per minute is {self.flow_rate_min} {self.flow_rate_units_min}\n"
                  f"The flow rate per second is {round(self.flow_rate_sec,2)} {self.flow_rate_units_sec}\n"
                  f"The # of micro steps is  {self.micro_steps}\n"
                  f"The # of motor steps is  {self.motor_steps}\n"
                  f"The gear box ratio is  {self.gearbox_ratio}\n"
                  f"The number of microsteps per revolution is {round(self.micro_steps_per_rev,2)}\n"
                  f"The Pump Head Volume is  {self.pump_head_volume}\n"
                  f"The Velocity Max is {round(self.steps_per_ul,2)} {self.steps_per_ul_units}"
                  )
        print(result)
        return result

    #Turns off serial connection and turned it off
    def stop(self) -> None:
        if not self.ser or not self.ser.is_open:
            print("Serial connection for VICI M6 Pumps is not open.")
            return
        print("Closing pumps.\n")
        #Sets the stop stop flag to true to stop the pump from moving
        self._stop_flag = True
        #Sets the flow rate to 0 overriding all previous commands
        self.send_command("SL 0")

    def stop_connection(self) -> None:
        if not self.ser:
            print("No serial connection to close.")
            return
        try:
            self.send_command("P=0")
            self.send_command("E")
            self.reset_parameters()
            self.ser.close()
            print('Serial connection closed.\n Pumps are closed.')
        except Exception as e:
            print(f"Error while stopping connection: {e}")

    def pump_solution(self, volume: float) -> None:
        try:
            self._stop_flag = False  # Reset stop flag at the start of pumping
            total_microsteps = int(self.steps_per_ul * volume)
            if self.flow_rate_sec == 0:
                raise ValueError("Flow rate cannot be zero.")

            pump_time = abs(volume / self.flow_rate_sec)

            # Set pump parameters
            commands = [
                f"A={self.A}", f"D={self.D}", f"VI={self.VI}", f"VM={self.VM}", f"P={self.P}", "PR P"
            ]
            for cmd in commands:
                self.send_command(cmd)

            self.send_command(f"MA={self.direction_multiplier * total_microsteps}")
            self.send_command("PR AL")

            # Wait for pumps to finish moving or for a stop signal 
            start_time = time.monotonic()
            while time.monotonic() - start_time < pump_time and not self._stop_flag:
                time.sleep(0.2)

            self.stop()
            print("Number of microsteps the pump moved:")
            self.send_command("PR P")
            print(f"Actual pump time: {time.time() - pump_time:.2f} seconds")
        except Exception as e:
            print(f"Error during pump operation: {e}")
    
    def aspirate(self, flow_rate: float, volume: float, action: str = "aspirating") -> None:
        self.start()
        self.set_flow_rate(abs(flow_rate), action)  # driver uses |rate|
        self.pump_solution(volume)  # <-- blocks here
        self.stop()
        
    def dispense(self, flow_rate: float, volume: float, action: str = "dispensing") -> None:
        self.start()
        self.set_flow_rate(abs(flow_rate), action)  # driver uses |rate|
        self.pump_solution(volume)  # <-- blocks here
        self.stop()

    def status(self) -> str | float:
        """Return current pump flow rate in uL/min, or a message if disconnected."""
        if not self.ser or not self.ser.is_open:
            return "VICI M6 Pump - Disconnected"

        # Ask pump for current velocity
        self.ser.write(b"PR V\r")

        # Read response line
        resp = self.ser.readline().decode().strip()

        # Make sure the response is a valid number
        try:
            steps_per_sec = float(resp)
        except ValueError:
            return f"Error: invalid velocity response '{resp}'"

        # Convert steps/sec → uL/min
        uL_per_min = (steps_per_sec / self.steps_per_ul) * 60.0

        return uL_per_min


    def reset_parameters(self) -> None:
        self.send_command("FD")
        self.send_command("IP")

    def close(self) -> None:
        """Closes the serial connection."""
        self.ser.close()

    def safe_shutdown(self, success: bool) -> None:
        self.stop()
        self.close()

