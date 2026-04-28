# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

'''
This module contains the Regio_ICC_Isametic_Pump class.
This class serves 
'''

# TODO: There are four seperate channels to control with this pump, we wish to have each channel register as a separate pump
# in the methods.py file, so that it would show up as four separate pumps when working in methods.py
# need to brainstorm how to implment in this code

import time
import serial
import math
from devices.industry_components.pumps.pumps import Pump

# TODO: I think the best way to implement this is to make a new peristaltic pump class
# this would inherit from the the pump class, I want this class to be able to set the the tubing size ID
# which would then be used to calculate the flow rate based on the rpm

class Regio_ICC_Isametic_Pump(Pump):

    def __init__(self,  port='COM16', baud_rate=9600, timeout=1):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.ser = None
        self._connected = False
    
    # ----------------------------------
    # Helper Functions
    # ----------------------------------
    def _get_firmware_version(self) -> None:
        "Gets the firmware version of the pump"
        self.ser.write("0(\r\n".encode())
        firmware_version = self.ser.readline().decode().strip()
        print(firmware_version)

    def _set_to_time_mode(self) -> None:
        "Sets the pump to time mode"
        self.ser.write("1N\r\n".encode())
        if "*" == self.ser.readline().decode().strip():
            print("Pump set to time mode")
        else:
            print("Failed to set pump to time mode")
            print(f"Pump response: {self.ser.readline().decode().strip()}")

    def _set_rpm(self, rpm: float) -> None:
        "Sets the RMP of the pump"
        self.rpm = rpm
        self.ser.write(f"{self.rpm}\r\n".encode())  
    
    def _set_direction(self, direction: str) -> None:
        "Sets the direction of the pump, either 'aspirating' or 'dispensing'"
        self.direction = direction
        if self.direction == 'aspirating':
            self.ser.write("1K\r\n".encode())
            if "*" == self.ser.readline().decode().strip():
                print("Direction set to aspirating")
            else: 
                print("Failed to set direction to aspirating")
        elif self.direction == 'dispensing':
            self.ser.write("1J\r\n".encode())
            if "*" == self.ser.readline().decode().strip():
                print("Direction set to dispensing")
            else:
                print("Failed to set direction to dispensing")
    
    def _get_direction(self) -> str:
        "Gets the current direction of the pump"
        self.ser.write("1xD\r\n".encode())
        direction_response = self.ser.readline().decode().strip()
        if direction_response == "K":
            print("Current direction: aspirating")
            return "aspirating"
        elif direction_response == "J":
            print("Current direction: dispensing")
            return "dispensing"
        else:
            print(f"Failed to get direction, response: {direction_response}")
            return "unknown"

    def _set_flow_rate(self, flow_rate_ul_min: float) -> None:
        """Implement logic to set flow rate for the Regio ICC Isametic Pump"""
        # TODO: Not sure what format the flow rate needs to be in for the pump commands
        flow_rate_ml_min = flow_rate_ul_min / 1000
        formatteed_flow_rate = self._format_flow_rate_input(flow_rate_ml_min)
        self.ser.write(f"1f{formatteed_flow_rate}\r\n".encode())
        echo = self.ser.readline().decode().strip()
        print(f"Flow rate set. Pump echo: {echo}")

    def _get_flow_rate(self) -> float:
        """Implement logic to get flow rate for the Regio ICC Isametic Pump"""
        self.ser.write("1f\r\n".encode())  # Example command to query flow rate
        flow_rate_response = self.ser.readline().decode().strip()
        print(f"Flow rate response: {self._format_flow_rate_output(flow_rate_response)} uL/min")  
        return self._format_flow_rate_output(flow_rate_response)

    def _set_run_time(self, flow_rate, volume) -> None:
        """Implement logic to set run time for the Regio ICC Isametic Pump"""
        # Currently it's only set to channel 1, need to implement for all channels
        run_time_sec = self._calculate_pump_time(flow_rate, volume)
        run_time_sec = int(run_time_sec * 10)
        run_time_str = f"{run_time_sec:08d}"
        self.ser.write(f"1xT{run_time_str}\r\n".encode())

    def _start(self):
        """Implement logic to start the pump"""
        # Currently it's only set to channel 1, need to implement for all channels
        self.ser.write("1H\r\n".encode())  # Example command to start the pump
        if "*" == self.ser.readline().decode().strip():
            print("Pump started successfully.")
    
    def _stop(self):
        """Implement logic to stop the pump"""
        # Currently it's only set to channel 1, need to implement for all channels
        self.ser.write("1I\r\n".encode())  # Example command to stop the pump
        if "*" == self.ser.readline().decode().strip():
            print("Pump stopped successfully.")

    def _status(self) -> str:
        """Implement logic to return the current status of the pump"""
        self.ser.write("1E\r\n".encode())  # Example command to query status
        status_response = self.ser.readline().decode().strip()
        if status_response == "+":
            print("Pump is running.")
        elif status_response == "-":
            print("Pump is stopped.")
        return status_response

    # ----------------------------------
    # Calculation Functions
    # ----------------------------------

    def _calculate_pump_time(self, flow_rate_uL_min: float, volume_ul: float) -> float:
        """Calculate the time required to pump a given volume at a specified flow rate"""
        time_sec = (volume_ul / flow_rate_uL_min) * 60  # Convert minutes to seconds
        return time_sec
    
    def _format_flow_rate_input(self, flow_rate_ml_min: float) -> str:
        """Convert a mL/min value to Flow Rate Type 2 format (mmmmEse)"""
        if flow_rate_ml_min == 0:
            return "0000E+0"
        
        exponent = math.floor(math.log10(abs(flow_rate_ml_min)))       
        mantissa = round(flow_rate_ml_min / (10 ** (exponent - 3)))  

        # The pump expects a format of mmmmEse, where mmmm is the mantissa and Ese is the exponent with a sign
        sign = "+" if exponent >= 0 else "-"
        return f"{mantissa:04d}{sign}{abs(exponent)}"
    
    def _format_flow_rate_output(self, response: str) -> float:
        # Converts mmmmEse — m.mmm x 10^(se) to units mL/min in float format
        mantissa_str, exp_str = response.split("E")
        # Example 5000E-4 would be parsed as mantissa_str = "5000" and exp_str = "-4"
        mantissa = int(mantissa_str) / 1000.0  
        exponent = int(exp_str)                 
        flow_rate_ml_min = mantissa * (10 ** exponent)
        flow_rate_ul_min = flow_rate_ml_min * 1000.0
        return flow_rate_ul_min


    # ----------------------------------
    # Core Pump Functions
    # ----------------------------------
    def connect(self) -> None:
        self.ser = serial.Serial(port=self.port, baudrate=self.baud_rate, timeout=self.timeout, bytesize=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE, parity=serial.PARITY_NONE)
        self._connected = True
        print("Successfully connected to Regio ICC Isametic Pump.")

    def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Implement aspirate logic for the Regio ICC Isametic Pump"""  
        self._set_direction('aspirating')
        self._set_to_time_mode()
        self._set_flow_rate(flow_rate_ul_min)      
        self._set_run_time(flow_rate_ul_min, volume_ul)
        self._start()
        time.sleep(self._calculate_pump_time(flow_rate_ul_min, volume_ul))  

    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Implement dispense logic for the Regio ICC Isametic Pump"""
        self._set_direction('dispensing')
        self._set_to_time_mode()
        self._set_flow_rate(flow_rate_ul_min)
        self._set_run_time(flow_rate_ul_min, volume_ul)
        self._start()
        time.sleep(self._calculate_pump_time(flow_rate_ul_min, volume_ul))

    def set_flow_rate(self, flow_rate_ul_min):
        """Implement logic to set flow rate for the Regio ICC Isametic Pump"""
        self._set_flow_rate(flow_rate_ul_min)

    def stop(self) -> None:
        """Implement stop logic for the Regio ICC Isametic Pump"""
        self._stop()

    def status(self) -> str:
        """Implement logic to return the current status of the Regio ICC Isametic Pump"""
        return self._status()

    def close(self) -> None:
        self.ser.close()
        self._connected = False
        print("Closed connection to Regio ICC Isametic Pump.")

    def safe_shutdown(self, success: bool) -> None:
        """Implement logic to safely shutdown the pump, ensuring it is in a safe state regardless of success or failure"""
        self.stop()  # Ensure the pump is stopped
        self.close()  # Close the connection

if __name__ == "__main__":
    TARGET_FLOW_RATE_UL_MIN = 500.0
    TARGET_VOLUME_UL = 100.0
    FLOW_RATE_TOLERANCE_PCT = 5.0   # Accept ±5% of the target flow rate
    POLL_INTERVAL_SEC = 0.5          # How often to check status and flow rate
 
    pump = Regio_ICC_Isametic_Pump(port='COM23', baud_rate=9600, timeout=1)
    success = False
 
    try:
        pump.connect()
 
        # Configure and start the pump manually so we can poll while it runs.
        pump._set_direction('aspirating')
        pump._set_to_time_mode()
        pump._set_flow_rate(TARGET_FLOW_RATE_UL_MIN)
        pump._set_run_time(TARGET_FLOW_RATE_UL_MIN, TARGET_VOLUME_UL)
        pump._start()
 
        run_time_sec = pump._calculate_pump_time(TARGET_FLOW_RATE_UL_MIN, TARGET_VOLUME_UL)
        elapsed = 0.0
 
        print(f"\nMonitoring pump — target: {TARGET_FLOW_RATE_UL_MIN} uL/min "
              f"for {run_time_sec:.1f} s ({TARGET_VOLUME_UL} uL)\n")
 
        while elapsed < run_time_sec:
            time.sleep(POLL_INTERVAL_SEC)
            elapsed += POLL_INTERVAL_SEC
 
            # 1. Confirm the pump is still running (command E, ref 6.21).
            status = pump._status()
            if status != "+":
                print(f"[{elapsed:.1f}s] WARNING: pump stopped unexpectedly (status='{status}'). Aborting.")
                break
 
            # 2. Read back actual flow rate (command f, ref 3.13) and compare to target.
            actual_flow_ul_min = pump._get_flow_rate()
            deviation_pct = abs(actual_flow_ul_min - TARGET_FLOW_RATE_UL_MIN) / TARGET_FLOW_RATE_UL_MIN * 100.0
 
            if deviation_pct <= FLOW_RATE_TOLERANCE_PCT:
                print(f"[{elapsed:.1f}s] OK   — actual: {actual_flow_ul_min:.2f} uL/min "
                      f"(deviation: {deviation_pct:.1f}%)")
            else:
                print(f"[{elapsed:.1f}s] WARN — actual: {actual_flow_ul_min:.2f} uL/min "
                      f"is outside ±{FLOW_RATE_TOLERANCE_PCT}% tolerance "
                      f"(deviation: {deviation_pct:.1f}%)")
 
        # Final status check after the run completes.
        final_status = pump._status()
        if final_status == "-":
            print("\nPump finished and is stopped — run completed successfully.")
            success = True
        else:
            print("\nWARNING: Pump is still running after expected run time. Stopping manually.")
            pump.stop()
 
    except Exception as e:
        print(f"Error during pump operation: {e}")
 
    finally:
        pump.safe_shutdown(success=success)
