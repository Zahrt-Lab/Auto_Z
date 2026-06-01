# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

from __future__ import annotations

import time

from utils.serial_DT_transporter import SerialDTTransport as serial_DT

class Tecan_driver():

  '''This class serves as a low-level driver for the Tecan pump.
    It handles serial communication and direct control of the pump hardware.
  '''      

  def __init__(self, port: str = 'COM16', baud_rate: int = 9600, timeout: int = 1) -> None:

    self.port: str = port
    self.baud_rate: int = baud_rate
    self.timeout: int = timeout
    self.ser: serial_DT = serial_DT(port=self.port, baud_rate=self.baud_rate, timeout=self.timeout)
    self.is_connected: bool = False
    self.address_A: int = 1
    self.address_B: int = 2

  def decode_pump_address(self, pump: str) -> int:

    if pump == "A":
      return self.address_A
    elif pump == "B":
      return self.address_B
    else:
      raise ValueError("Invalid pump selection. Choose 'A' or 'B'.")
    
  def connect(self) -> None:

    if self.is_connected:
      print("Serial connection already established.")
      return
    try:
      self.ser.connect()
      self.is_connected = True
    except Exception as e:
      print(f"Error connecting to Tecan pump: {e}")
  
  def disconnect(self) -> None:

    if self.is_connected:
      self.ser.disconnect()
      self.is_connected = False
    
  def initialize_pump(self, pump: str = "A", resolution: int = 0) -> None:

    if not self.is_connected:
      print("Serial connection not established. Cannot initialize pump.")
      return
    try:
      addr = self.decode_pump_address(pump)
      self.ser.send_command(f"/{addr}N{resolution}ZR")
    except Exception as e:
      print(f"Error initializing pump: {e}")

  def start_pump(self, speed: float, pump: str = "A",) -> None:

    if not self.is_connected:
      print("Serial connection not established. Cannot run pump.")
      return
    try:
      addr = self.decode_pump_address(pump)
      command = f"/{addr}V{speed}IA3000gOA0IA3000GR"
      self.ser.send_command(command)
    except Exception as e:
      print(f"Error running pump: {e}")
    
  def stop_pump(self, pump: str = "A") -> None:

    if not self.is_connected:
      print("Serial connection not established. Cannot stop pump.")
      return
    try:
      addr = self.decode_pump_address(pump)
      self.ser.send_command(f"/{addr}T")
    except Exception as e:
      print(f"Error stopping pump: {e}")

  def send_command(self, command: str) -> None:

    if not self.is_connected:
      print("Serial connection not established. Cannot send command.")
      return
    try:
      self.ser.send_command(command)
    except Exception as e:
      print(f"Error sending command: {e}")
  
  def read_response(self) -> str:

    if not self.is_connected:
      print("Serial connection not established. Cannot read response.")
      return ""
    try:
      return self.ser.read_response()
    except Exception as e:
      print(f"Error reading response: {e}")
      return ""
  
  def query(self, command: str) -> str:

    if not self.is_connected:
      print("Serial connection not established. Cannot query pump.")
      return ""
    try:
      return self.ser.query(command)
    except Exception as e:
      print(f"Error querying pump: {e}")
      return ""
  
  def is_initialized(self, pump: str = "A") -> bool:
   
    #Require some testing with actual hardware
    if not self.is_connected:
      print("Serial connection not established. Cannot check initialization status.")
      return False
    is_initialized = False
    for i in range(2): # Try up to 2 times to check initialization status
      try:
        addr = self.decode_pump_address(pump)
        self.ser.send_command(f"/{addr}S14D1R") # For some reason, the command must be sent twice
        time.sleep(0.1) # Small delay to allow device to process command
        response = self.ser.read_response()
        decoded_response = self.ser.parse_dt_response(response)
        status_char = decoded_response["status"]
        error_code = ord(status_char) & 0x0F # Extract the error code from the status character
        #return status_char, error_code
        if error_code != 7 and status_char != "O":
           #According to the Tecan documentation, error code 7 indicates "Pump not initialized"
           is_initialized = True
           
    
      except Exception as e:
        print(f"Error checking initialization status: {e}")
        return False
    return is_initialized
    
  def check_until_initialized(self, pump: str = "A", timeout: float = 60.0) -> None:
    """Check if the specified pump is initialized, with a timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
      if self.is_initialized(pump):
        print(f"Pump {pump} is initialized? {self.is_initialized(pump)}.")
        return True
      print(f"Waiting for pump {pump} to initialize...")
      time.sleep(5)  # Wait for 5 seconds before checking again
    print(f"Timeout reached while waiting for pump {pump} to initialize.")
  
  def is_running(self, pump: str = "A") -> bool:
    #todo: implement method to check if pumps are running
    pass

  def run_continuous_flow(self,
                          resolution: int = 1,
                          initial_speed: int = 4000,
                          aspirate_speed: int = None,
                          dispense_speed: int = 3000,
                          initial_position: int = 0,
                          final_position: int = 24000) -> None:
    if not self.is_connected:
      print("Serial connection not established. Cannot run continuous flow.")
      return
    try:
      command_A = self.compose_command_continuous_flow_A(resolution=resolution, initial_speed=initial_speed, aspirate_speed=aspirate_speed, dispense_speed=dispense_speed, initial_position=initial_position, final_position=final_position)
      command_B = self.compose_command_continuous_flow_B(resolution=resolution, initial_speed=initial_speed, aspirate_speed=aspirate_speed, dispense_speed=dispense_speed, initial_position=initial_position, final_position=final_position)
      self.ser.send_command(command_A)
      time.sleep(0.1) # Small delay to allow device to process command
      self.ser.send_command(command_B)
    except Exception as e:
      print(f"Error running continuous flow: {e}")

  def compose_command_continuous_flow_A(self,
                                        resolution = 2,
                                        initial_speed = 4000,
                                        aspirate_speed = None,
                                        dispense_speed = 3000,
                                        initial_position = 0,
                                        final_position = 24000) -> str:
    """Compose a command string for continuous flow for pump A at the specified rate.
    Arguments:
        rate_counts_s : int
            The flow rate in counts per second.
    Returns:
        str
            The composed command string for continuous flow.
    """
    if aspirate_speed is None:
        aspirate_speed = dispense_speed * 2
        
    if aspirate_speed < dispense_speed * 2:
        raise ValueError("Aspirate speed must be at least twice the dispense speed.")   
    
    command = f"/1N{resolution}J7V{initial_speed}IA{final_position}V{dispense_speed}OA{initial_position}J0V{aspirate_speed}IA{final_position}gH0J7V{dispense_speed}OA{initial_position}J0V{aspirate_speed}IA{final_position}GR"
    
    return command

  def compose_command_continuous_flow_B(self, resolution = 2,
                                        initial_speed = 4000,
                                        aspirate_speed = None,
                                        dispense_speed = 3000, 
                                        initial_position = 0, 
                                        final_position = 24000) -> str:
      """Compose a command string for continuous flow for pump B at the specified rate.
    
      Arguments:
          rate_counts_s : int
              The flow rate in counts per second.
      Returns:
          str
              The composed command string for continuous flow.
      """
      if aspirate_speed is None:
        aspirate_speed = dispense_speed * 2

      if aspirate_speed < dispense_speed * 2:
        raise ValueError("Aspirate speed must be at least twice the dispense speed.")
    
      command = f"/2N{resolution}J7V{initial_speed}IA{final_position}gH0J7V{dispense_speed}OA{initial_position}J0V{aspirate_speed}IA{final_position}GR"
    
      return command
  
  #todo: implement method to detect if valve is in output position. This will be used to determine when start counting the volume ispensed in the continous flow
  def is_valve_in_output_position(self, pump: str = "A") -> bool:
    # the command ?6 returs the valve position. I believe it is i for input and o for output.
    # Check if is connected 
    if not self.is_connected:
      print("Serial connection not established. Cannot check valve position.")
      return False
    try:
      addr = self.decode_pump_address(pump)
      self.ser.send_command(f"/{addr}?6")
      time.sleep(0.1) # Small delay to allow device to process command
      response = self.ser.read_response()
      decoded_response = self.ser.parse_dt_response(response)
      valve_position = decoded_response["data"] # Assuming the valve position is in the "data" field of the response
      return valve_position == str(3) # Return True if valve is in output position, False otherwise
    except Exception as e:
      print(f"Error checking valve position: {e}")
      return False
    
  def compose_aspirate_command(self,
                                pump: str = "A",
                                resolution: int = 2,
                                speed: int = 4000,
                                position: int = 24000) -> str:
    """Compose a command string for aspirating with the specified pump at the specified speed and position.
    Arguments:
        pump : str
            The pump to use ("A" or "B").
        resolution : int
            The resolution to use for the command.
        speed : int
            The speed to use for the command.
        position : int
            The position to use for the command.
    Returns:
        str
            The composed command string for aspirating.
    """

    addr = self.decode_pump_address(pump)
    command = f"/{addr}N{resolution}V{speed}IA{position}OR"
    return command

  def run_aspirate(self,
                        pump: str = "A",
                        resolution: int = 1,
                        aspirate_speed: int = 4000,
                        final_position: int = 24000) -> None:
      
      '''This method sends the command to the pump to start aspirating.
      '''
      if not self.is_connected:
          print("Serial connection not established. Cannot run aspirate.")
          return  
      try:
        command = self.compose_aspirate_command(pump, resolution, aspirate_speed, final_position)
        self.send_command(command)
      except Exception as e:
        print(f"Error running aspirate: {e}")

  def compose_dispense_command(self,
                                pump: str = "A",
                                resolution: int = 1,
                                speed: int = 3000,
                                position: int = 0) -> str:
    """Compose a command string for dispensing with the specified pump at the specified speed and position.
    Arguments:
        pump : str
            The pump to use ("A" or "B").
        resolution : int

        speed : int
            The speed to use for the command.
        position : int
            The position to use for the command.
    Returns:
        str
            The composed command string for dispensing.
    """
    addr = self.decode_pump_address(pump)
    command = f"/{addr}N{resolution}V{speed}OA{position}IR"
    return command
  
  def run_dispense(self,
                        pump: str = "A",
                        resolution: int = 1,
                        dispense_speed: int = 3000,
                        final_position: int = 0) -> None:
      
      '''This method sends the command to the pump to start dispensing.
      '''
      if not self.is_connected:
          print("Serial connection not established. Cannot run dispense.")
          return  
      try:
        command = self.compose_dispense_command(pump, resolution, dispense_speed, final_position)
        self.send_command(command)
      except Exception as e:
        print(f"Error running dispense: {e}")
