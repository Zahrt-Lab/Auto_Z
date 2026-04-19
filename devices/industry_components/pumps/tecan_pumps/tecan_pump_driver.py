# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

from utils.serial_DT_transporter import SerialDTTransport as serial_DT

class Tecan_driver():

  '''This class serves as a low-level driver for the Tecan pump.
    It handles serial communication and direct control of the pump hardware.
  '''      

  def __init__(self,port='COM16', baud_rate=9600, timeout=1):

    self.port = port
    self.baud_rate = baud_rate
    self.timeout = timeout
    self.ser = serial_DT(port=self.port, baud_rate=self.baud_rate, timeout=self.timeout)
    self.is_connected = False
    self.address_A  = 1
    self.address_B = 2

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
  
  def is_initialized(self, pump: str = "A") -> bool:

    #Require some testing with actual hardware
    if not self.is_connected:
      print("Serial connection not established. Cannot check initialization status.")
      return False
    try:
      addr = self.decode_pump_address(pump)
      self.ser.send_command(f"/{addr}Q")
      response = self.ser.read_response()
      decoded_response = self.ser.parse_dt_response(response)
      status_char = decoded_response["status"]
      error_code = ord(status_char) & 0x0F # Extract the error code from the status character
      return error_code != 7 #According to the Tecan documentation, error code 7 indicates "Pump not initialized"
    
    except Exception as e:
      print(f"Error checking initialization status: {e}")
      return False
    
    def check_until_initialized(self, pump: str = "A", timeout: float = 60.0) -> bool:
      """Check if the specified pump is initialized, with a timeout."""
      start_time = time.time()
      while time.time() - start_time < timeout:
        if self.is_initialized(pump):
          return True
        print(f"Waiting for pump {pump} to initialize...")
        time.sleep(5)  # Wait for 5 seconds before checking again
      print(f"Timeout reached while waiting for pump {pump} to initialize.")
      return False
  
  def is_running(self, pump: str = "A") -> bool:
    #todo: implement method to check if pumps are running
    pass

  def run_continuous_flow(self,
                          resolution: int = 0,
                          initial_speed: float = 26000,
                          aspirate_speed: float = None,
                          dispense_speed: float = 1000,
                          initial_position: int = 0,
                          final_position: int = 3000,
                          j_value: int = 1000) -> None:
    if not self.is_connected:
      print("Serial connection not established. Cannot run continuous flow.")
      return
    try:
      command_A = self.compose_command_continuous_flow_A(resolution=resolution, initial_speed=initial_speed, aspirate_speed=aspirate_speed, dispense_speed=dispense_speed, initial_position=initial_position, final_position=final_position, j_value=j_value)
      command_B = self.compose_command_continuous_flow_B(resolution=resolution, initial_speed=initial_speed, aspirate_speed=aspirate_speed, dispense_speed=dispense_speed, initial_position=final_position, final_position=final_position, j_value=j_value)
      self.ser.send_command(command_A)
      self.ser.send_command(command_B)
    except Exception as e:
      print(f"Error running continuous flow: {e}")

  def compose_command_continuous_flow_A(resolution = 2,
                                      initial_speed = 26000,
                                      aspirate_speed = None,
                                        dispense_speed = 1000,
                                        initial_position = 0,
                                        final_position = 192000,
                                        j_value = 1000) -> str:
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
    
    command = f"N{resolution}J7V{initial_speed}IA{final_position}OV{dispense_speed}j{j_value}0A{initial_position}IV{aspirate_speed}A{final_position}gJ7H0OV{dispense_speed}j{j_value}0A{initial_position}IV{aspirate_speed}A{final_position}GR"
    
    return command

def compose_command_continuous_flow_B(resolution = 2,
                                      initial_speed = 26000,
                                      aspirate_speed = None,
                                      dispense_speed = 1000, 
                                      initial_position = 0, 
                                      final_position = 192000, 
                                      j_value = 1000) -> str:
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
    
    command = f"N{resolution}J7V{initial_speed}IA{final_position}gJ7H0OV{dispense_speed}j{j_value}0A{initial_position}IV{aspirate_speed}A{final_position}GR"
    
    return command
  
