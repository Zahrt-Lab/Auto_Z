# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

import serial
import time

class Serial_DT_Transporter():

    '''This class serves as a low-level driver for the serial communication with the DT transporter.
        It handles serial communication and direct control of the transporter hardware.
    '''      

    def __init__(self,port='COM16', baud_rate=9600, timeout=1):

        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.ser = None
        self.is_connected = False

    def connect(self) -> None:

        if self.ser is not None and self.ser.is_open:
            print("Serial connection already established.")
            return
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
        except serial.SerialException as e:
            print(f"Error initializing serial connection: {e}")
  
    def disconnect(self) -> None:

        if self.ser is not None and self.ser.is_open:
            self.ser.close()
            self.ser = None

    def send_command(self, command: str) -> None:

      if self.ser is None or not self.ser.is_open:
        print("Serial connection not established. Cannot send command.")
        return
      try:
        self.ser.write(command.encode())
      except serial.SerialException as e:
        print(f"Error sending command: {e}")
    
    def read_response(self) -> str:

      if self.ser is None or not self.ser.is_open:
        print("Serial connection not established. Cannot read response.")
        return ""
      try:
        response = self.ser.readline().decode().strip()
        return response
      except serial.SerialException as e:
        print(f"Error reading response: {e}")
        return ""

  