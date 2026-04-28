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

  def __init__(self, port='COM16', baud_rate=9600, timeout=1, name="Tecan_pump_1"):
    self.name = name
    self.flow_rate_ul_min = 0
    
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

    '''
  def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
    self.set_flow_rate(flow_rate_ul_min) # Set the flow rate for the pump
    #The dispense command in the Tecan Pump is the continuous flow command
    time_sec = self._calculate_time_for_volume(volume_ul)
    speed = int (self._calculate_speed_for_flow_rate())
    print(f"Time (s): {time_sec}")
    print(f"Speed: {speed}")
    self.driver.run_continuous_flow(dispense_speed=speed)
    #The time should only start after the pump has filled its barrel and moved the valve to the output position.
    #This is why we need check untill the valve is in the output mode
    print("Waiting for pump A valve to be in output position...")
    while not self.driver.is_valve_in_output_position(pump="A"):
      time.sleep(0.1)  # Wait for 0.1 seconds before checking again
    print("Pump A valve is in output position. Starting dispense timer.")
    start_time = time.monotonic()
    while True:
      elapsed_time = time.monotonic() - start_time
      dispensed_volume = min(volume_ul, (elapsed_time / time_sec) * volume_ul) if time_sec > 0 else volume_ul
      print(f"Dispensed: {dispensed_volume:.2f} uL / {volume_ul:.2f} uL")

      remaining_time = time_sec - elapsed_time
      if remaining_time <= 0:
        break
      time.sleep(min(10, remaining_time))

    self.stop()  # Stop the pump after dispensing the desired volume
  '''
  
  def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:

    self.set_flow_rate(flow_rate_ul_min) # Set the flow rate for the pump
    #The dispense command in the Tecan Pump is the continuous flow command
    time_sec = self._calculate_time_for_volume(volume_ul)
    dispense_speed = int (self._calculate_speed_for_flow_rate())
    print(f"Time (s): {time_sec}")
    print(f"Speed: {dispense_speed}")
    aspirate_speed = dispense_speed * 2
    initial_aspirate_speed = 4000 #This is faster so the pump can reach the position to begin quickly
    self.driver.run_aspirate(pump="A", resolution=2, aspirate_speed=initial_aspirate_speed, final_position=24000) # Start aspirating at a high speed to quickly reach the position
    time.sleep(0.1) # Wait for a short time to allow the pump to start aspirating
    self.driver.run_aspirate(pump="B", resolution=2, aspirate_speed=initial_aspirate_speed, final_position=24000) # Aspirate pump B
    time.sleep(0.1) # Wait for a short time to allow the pump to start aspirating
    while not self.driver.is_valve_in_output_position(pump="A"):
      time.sleep(0.1)  # Wait for 0.1 seconds before checking again
    print("Pump A valve is in output position. Starting dispense timer.")    
    #The continuous flow control starts now
    time_now = time.monotonic()
    mode = 1 # 1: Pump A dispensing and B aspirating; 2: Pump A aspirating and B dispensing
    while time.monotonic() - time_now < time_sec:
      if mode == 1:
        self.driver.run_dispense(pump="A", resolution=2, dispense_speed=dispense_speed, final_position=24000) # Start dispensing from pump A
        time.sleep(0.1) # Wait for a short time to allow the pump to start dispensing
        self.driver.run_aspirate(pump="B", resolution=2, aspirate_speed=aspirate_speed, final_position=24000) # Start aspirating from pump B
        time.sleep(0.1) # Wait for a short time to allow the pump to start aspirating
        while self.driver.is_valve_in_output_position(pump="A") and time.monotonic() - time_now < time_sec:
          time.sleep(0.1)  # Wait for 0.1 seconds before checking again
        mode = 2
      else:
        self.driver.run_aspirate(pump="A", resolution=2, aspirate_speed=aspirate_speed, final_position=24000) # Start aspirating from pump A
        time.sleep(0.1) # Wait for a short time to allow the pump to start aspirating
        self.driver.run_dispense(pump="B", resolution=2, dispense_speed=dispense_speed, final_position=24000) # Start dispensing from pump B
        time.sleep(0.1) # Wait for a short time to allow the pump to start dispensing
        while self.driver.is_valve_in_output_position(pump="B") and time.monotonic() - time_now < time_sec:
          time.sleep(0.1)  # Wait for 0.1 seconds before checking again
        mode = 1
      elapsed_time = time.monotonic() - time_now
      dispensed_volume = min(volume_ul, (elapsed_time / time_sec) * volume_ul) if time_sec > 0 else volume_ul
      print(f"Dispensed: {dispensed_volume:.2f} uL / {volume_ul:.2f} uL")

      remaining_time = time_sec - elapsed_time
      if remaining_time <= 0:
        break
      time.sleep(min(10, remaining_time))
    
    self.stop()  # Stop the pump after dispensing the desired volume
    
  def _calculate_time_for_volume(self, volume_ul: float) -> float:
    """Helper method to calculate the time required to dispense a given volume at a specified flow rate."""
    time_min = volume_ul / self.flow_rate_ul_min  # time in minutes
    return time_min * 60  # convert to seconds
  
  def _calculate_speed_for_flow_rate(self) -> float:
    """Helper method to calculate the pump speed setting for a given flow rate.
    Calibration was performed by Joao on 2026-04-21, and found that speed (pulses/sec) = flow_rate (uL/min) * 0.2055"""
    speed = self.flow_rate_ul_min * 0.2055
    #todo: find another way to constrain the speed. The speed should not be smaller that 5
    if speed < 5:
      speed = 5
    return speed 

  def set_flow_rate(self, flow_rate_ul_min: float) -> None:
    self.flow_rate_ul_min = flow_rate_ul_min

  def stop(self) -> None:
    if not self.driver.is_connected:
      return
    self.driver.stop_pump(pump="A")
    self.driver.stop_pump(pump="B")

  def status(self) -> str:
    #todo: implement status logic using Tecan_driver
    return "Status command is not implemented yet."

  def close(self) -> None:
    if not self.driver.is_connected:
      return
    self.stop()  # Ensure the pump is stopped before closing the connection
    self.driver.disconnect()

  def safe_shutdown(self, success: bool) -> None:
    if not self.driver.is_connected:
      return
    self.stop()  # Ensure the pump is stopped before closing the connection
    self.driver.disconnect()

  def calibrate(self, speed: float = 1000, time_sec: float = 60) -> None:
    '''Method to calibrate the pump. It takes volume, speed and time as input
    the experimentalist should runt the calibration method and measure the amount of water
    dispensed by the pump at different speeds. This will allow the experimentalist to create 
    a relationship between speed and uL/min
    '''
    self.driver.run_continuous_flow(dispense_speed=speed)

    while not self.driver.is_valve_in_output_position(pump="A"):
      print("Waiting for pump A valve to be in output position...")
      time.sleep(0.1)  # Wait for 0.1 seconds before checking again
    start_time = time.monotonic()
    while True:
      elapsed_time = time.monotonic() - start_time
      print(f"Elapsed Time: {elapsed_time:.2f} seconds / {time_sec:.2f} seconds")

      remaining_time = time_sec - elapsed_time
      if remaining_time <= 0:
        break
      time.sleep(min(10, remaining_time))

    self.driver.stop_pump(pump="A")
    self.driver.stop_pump(pump="B")

    print(f"Calibration complete. Speed: {speed} pulses/s, Time: {time_sec} seconds")
    print(f"Measure the actual volume dispensed and use this information to create a calibration curve relating speed to flow rate.")


