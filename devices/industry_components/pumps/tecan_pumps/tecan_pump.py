# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------


import time

from devices.industry_components.pumps.pumps import Pump
from devices.industry_components.pumps.tecan_pumps.tecan_pump_driver import Tecan_driver as driver


class Tecan_pump(Pump):
  '''This class serves as an abstraction layer for the Tecan pump.
  It inherits from the abstract Pump class and implements the 
  required methods. It uses the Tecan_driver to communicate with 
  the pump hardware.'''

  def __init__(self, port='COM16', baud_rate=9600, timeout=1):
    try:
      self.driver = driver(port=port, baud_rate=baud_rate, timeout=timeout)
    except Exception as e:
      print(f"Error initializing Tecan pump driver: {e}")
    
  def connect(self) -> None:       
    try:
      self.driver.connect()
    except Exception as e:
      print(f"Error connecting to Tecan pump: {e}")

    #Joao made the decision to initialize the pumps during the connect phase. This could also be moved to its own method.
    if self.driver.is_initialized("A"):
      print("Pump A is already initialized.")
    else:
      self.driver.initialize_pump(pump="A", resolution=0)
      print("Initializing pump A.")
    if self.driver.is_initialized("B"):
      print("Pump B is already initialized.")
    else:
      self.driver.initialize_pump(pump="B", resolution=0)
      print("Initializing pump B.")
    
    self.driver.check_until_initialized(pump="A", timeout=60) #Check until pump A is initialized before proceeding
    self.driver.check_until_initialized(pump="B", timeout=60) #Check until pump B is initialized before proceeding

  def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
    #Aspirate command is not implemented in the Tecan pump
    print("Aspirate command is not supported by Tecan pump.")
    pass

  def dispense(self, volume_ul: float) -> None:
    #todo: implement dispense logic using Tecan_driver
    #The dispense command in the Tecan Pump is the continuous flow command
      time_sec = self._calculate_time_for_volume(volume_ul)
      speed = int (self._calculate_speed_for_flow_rate())
      print(f"Time (s): {time_sec}")
      print(f"Speed: {speed}")
      self.driver.run_continuous_flow(dispense_speed=speed)

      #The time should only start after the pump has filled its barrel and moved the valve to the output position.
      #This is why we need check untill the valve is in the output mode

      while not self.driver.is_valve_in_output_position(pump="A"):
        print("Waiting for pump A valve to be in output position...")
        time.sleep(0.5)  # Wait for 0.5 seconds before checking again

      start_time = time.monotonic()
      while True:
        elapsed_time = time.monotonic() - start_time
        dispensed_volume = min(volume_ul, (elapsed_time / time_sec) * volume_ul) if time_sec > 0 else volume_ul
        print(f"Dispensed: {dispensed_volume:.2f} uL / {volume_ul:.2f} uL")

        remaining_time = time_sec - elapsed_time
        if remaining_time <= 0:
          break
        time.sleep(min(1, remaining_time))

      self.stop()  # Stop the pump after dispensing the desired volume
  
  def _calculate_time_for_volume(self, volume_ul: float) -> float:
    """Helper method to calculate the time required to dispense a given volume at a specified flow rate."""
    time_min = volume_ul / self.flow_rate_ul_min  # time in minutes
    return time_min * 60  # convert to seconds
  
  def _calculate_speed_for_flow_rate(self) -> float:
    """Helper method to calculate the pump speed setting for a given flow rate."""
    #For the tecan pump, the speed is independent of the resolution.
    # Considering the resolution = 0, the relationship of steps (up to 3000) and pulses (speed) is approximate
    # 0.45 steps/pulse. The relationship of steps to uL depends on the syringe and the calibration.
    # Considering the 500 uL syringe, 3000 steps corresponds to 500 uL, so 1 step corresponds to 0.1667 uL. Therefore, 1 pulse (at resolution 0) corresponds to 0.075 uL.
    uL_per_pulse = 0.075
    pulse_per_uL = 1 / uL_per_pulse
    #if flow rate is uL/min, then speed in pulses per minute is flow_rate_ul_min * pulse_per_uL
    pulses_per_minute = self.flow_rate_ul_min * pulse_per_uL
    #But Tecan pump speed is in pulses per second, so we need to convert minutes to seconds
    speed = pulses_per_minute / 60  # convert to pulses per second  
    return speed 

  def set_flow_rate(self, flow_rate_ul_min: float) -> None:
    self.flow_rate_ul_min = flow_rate_ul_min

  def stop(self) -> None:
    self.driver.stop_pump(pump="A")
    self.driver.stop_pump(pump="B")

  def status(self) -> str:
    #todo: implement status logic using Tecan_driver
    return "Status command is not implemented yet."

  def close(self) -> None:
    self.stop()  # Ensure the pump is stopped before closing the connection
    self.driver.disconnect()

  def safe_shutdown(self, success: bool) -> None:
    self.stop()  # Ensure the pump is stopped before closing the connection
    self.driver.disconnect()



