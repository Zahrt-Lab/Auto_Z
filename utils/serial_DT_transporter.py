# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

import serial
import time

class SerialDTTransport():

    """Low-level serial transport for DT/Tecan communication."""     

    def __init__(self,port='COM16', baud_rate=9600, timeout=1):

        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.ser = None

    @property
    def is_connected(self) -> bool:
        return self.ser is not None and self.ser.is_open
    
    def connect(self) -> None:

        if self.is_connected:
            print("Serial connection already established.")
            return
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
        except serial.SerialException as e:
            print(f"Error initializing serial connection: {e}")
  
    def disconnect(self) -> None:

        if self.is_connected:
            self.ser.close()
            self.ser = None

    def send_command(self, command: str) -> None:

      if not self.is_connected:
        raise RuntimeError("Serial connection not established. Cannot send command.") 
      try:
        self.ser.reset_input_buffer()  # Clear any existing data
        self.ser.reset_output_buffer() # Clear any existing data
        full_command = command + "\r"  # Append ETX, CR, LF
        self.ser.write(full_command.encode())
        self.ser.flush()  # Ensure command is sent immediately
        time.sleep(0.1)  # Small delay to allow device to process command
      except serial.SerialException as e:
        print(f"Error sending command: {e}")
    
    def read_response(self) -> str:

      if not self.is_connected:
        raise RuntimeError("Serial connection not established.")

      raw = self.ser.read_until(b"\x03")   # read through ETX
      tail = self.ser.read(2)              # consume CR LF

      if not raw:
        raise TimeoutError("No response from pump.")

      full_response = raw #+ tail
      return full_response.decode("ascii", errors="replace")

    def query(self, command: str) -> str:

      self.send_command(command)
      time.sleep(0.5)  # Small delay to allow device to process command
      return self.read_response()
  
    def parse_dt_response(self, response: str) -> dict:

      """
      Parse a DT protocol response string.

      Expected format:
        /0<status><data><ETX><CR><LF>

      Returns only the important parts.
      """
      
      if not response:
        raise ValueError("Empty response (no data received).")

      if response[0] != "/":
        raise ValueError(f"Invalid start of response: {response!r}")

      if len(response) < 3:
        raise ValueError(f"Incomplete response (no status): {response!r}")

      etx_index = response.find("\x03")
      if etx_index == -1:
        raise ValueError(f"Incomplete response (missing ETX): {response!r}")

      status = response[2]  # always exists if valid
      data = response[3:etx_index]

      return {
        "status": status,
        "data": data,
      }