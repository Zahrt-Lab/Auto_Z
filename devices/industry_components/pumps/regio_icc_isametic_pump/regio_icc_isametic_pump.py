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
from devices.industry_components.pumps.pumps import Pump

class Regio_ICC_Isametic_Pump(Pump):

    def connect(self) -> None:
        # Implement connection logic to the Regio ICC Isametic Pump
        pass

    def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        # Implement aspirate logic for the Regio ICC Isametic Pump
        pass

    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        # Implement dispense logic for the Regio ICC Isametic Pump
        pass

    def set_flow_rate(self, flow_rate_ul_min: float) -> None:
        # Implement logic to set flow rate for the Regio ICC Isametic Pump
        pass

    def stop(self) -> None:
        # Implement logic to stop the Regio ICC Isametic Pump
        pass

    def status(self) -> str:
        # Implement logic to return the current status of the Regio ICC Isametic Pump
        pass

    def close(self) -> None:
        # Implement logic to close the connection to the Regio ICC Isametic Pump
        pass

    def safe_shutdown(self, success: bool) -> None:
        # Implement any device-specific state cleanup before shutdown
        pass
