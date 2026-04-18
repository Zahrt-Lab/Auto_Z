# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------


from devices.industry_components.pumps.pumps import Pump
from devices.industry_components.pumps.tecan_pumps.tecan_pump_driver import Tecan_driver as driver


class Tecan_pump(Pump):
  '''This clas serves as an abstraction layer for the Tecan pump.
  It inherits from the abstract Pump class and implements the 
  required methods. It uses the Tecan_driver to communicate with 
  the pump hardware.'''

  def __init__(self, port='COM16', baud_rate=9600, timeout=1):
    #todo: initialize Tecan_driver with the provided connection parameters
    pass
    
  def connect(self) -> None:        
    #todo: implement connection logic using Tecan_driver
    pass

  def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
    #todo: implement aspirate logic using Tecan_driver
    pass

  def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
    #todo: implement dispense logic using Tecan_driver
    pass

  def set_flow_rate(self, flow_rate_ul_min: float) -> None:
    #todo: implement set_flow_rate logic using Tecan_driver
    pass

  def stop(self) -> None:
    #todo: implement stop logic using Tecan_driver
    pass

  def status(self) -> str:
    #todo: implement status logic using Tecan_driver
    pass

  def close(self) -> None:
    #todo: implement close logic using Tecan_driver
    pass

  def safe_shutdown(self, success: bool) -> None:
    #todo: implement safe_shutdown logic using Tecan_driver
    pass



