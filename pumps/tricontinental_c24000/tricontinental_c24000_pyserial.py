# Standalone code to control Tricontinental C24000 pump via PySerial
# In the future, this code can be imported into the tricontinental_c24000.py file.
# ------------------------------------------------------------------------------

# Import necessary libraries

import serial
import time

# Open serial communication with the pump
def connect(port, baudrate=9600, timeout=1):
    ser = serial.Serial(port, baudrate,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=timeout)
    time.sleep(2)  # Wait for the connection to establish
    return ser

# Close serial communication with the pump
def disconnect(ser):
    ser.close()
# Functions to be implemented:
# A general function to send commands to the pump

# Testing function
def send_DT(ser):
    """Send a firmware query command to the pump and print the response.
    Used for testing only.
    """
    # Clear input and output buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    # ---- COMMAND ----
    cmd = b"/1&\r"       # firmware query, CR terminated
    print("TX bytes:", cmd)

    ser.write(cmd)
    ser.flush()

    # Give pump time to respond
    time.sleep(0.2)

    # Read whatever is available
    n = ser.in_waiting
    print("Bytes waiting:", n)

    if n > 0:
        resp = ser.read(n)
        print("RX raw bytes:", resp)
    else:
        print("No response")

# Compose command string
def compose_command(pump_addr: int = 1, eeprom_addr: int = None, command: str = "&") -> str:
    """Compose a command string for a specific pump and EEPROM address.
    Arguments:
        pump_addr : str
            The address of the pump (e.g., '/1' for Pump A).
        eeprom_addr : str
            The EEPROM address (e.g., 's0' for EEPROM 0).
        command : str
            The command string to be composed.
    Returns:
        str
            The composed command string.
    """
    return f"/{pump_addr}{eeprom_addr}{command}\r"
# Function to store command in eeprom

# Function to translate pump letter to address
def pump_letter_to_address(pump: str) -> int:
    """Translate pump letter to address.
    Arguments:
        pump : str
            The pump letter (e.g., 'A' or 'B').
    Returns:
        int
            The corresponding pump address (1 for Pump A, 2 for Pump B).
    """
    if pump == "A":
        return 1
    elif pump == "B":
        return 2
    else:
        raise ValueError("Invalid pump selection. Choose 'A' or 'B'.")

def store_command(ser, pump="A", eeprom_addr=0, command="&"):
    """Store a command in the pump's EEPROM.
    Pump A: addr =/1
    PumpB: addr =/2
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump : str
            The pump address (e.g., 'A' for Pump A).
        eeprom_addr : int
            The EEPROM address (e.g., 0 for EEPROM 0).
        command : str
            The command string to store in the EEPROM.
    """
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    pump_addr = pump_letter_to_address(pump)
    full_command = f"/{pump_addr}s{eeprom_addr}{command}\r"
    print(f"Store: {pump}<-{full_command}")
    
    ser.write(full_command.encode())
    ser.flush()
    time.sleep(0.1)  # Small delay to ensure command is sent
    response = read_response(ser)
    print(f"Store: {pump}->{response}")

# Function to execute command stored in eeprom
def execute_command(ser, pump="A", eeprom_addr=0):
    """Execute a command stored in the pump's EEPROM.
    Pump A: addr =/1
    PumpB: addr =/2
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump : str
            The pump address (e.g., 'A' for Pump A).
        eeprom_addr : int
            The EEPROM address (e.g., 0 for EEPROM 0).
    """

    ser.reset_input_buffer()
    ser.reset_output_buffer()

    pump_addr = pump_letter_to_address(pump)
    full_command = f"/{pump_addr}e{eeprom_addr}R\r"
    print(f"Exec: {pump}<-{full_command}")
    
    ser.write(full_command.encode())
    ser.flush()
    time.sleep(0.1)  # Small delay to ensure command is sent
    response = read_response(ser)
    print(f"Exec: {pump}->{response}")

# Send command to pump
def send_command(ser, pump="A", command="&"):
    """Send a command to a specific pump (no eeprom involved).
    Pump A: addr =/1
    PumpB: addr =/2
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump : str
            The pump address (e.g., 'A' for Pump A).
        command : str
            The command string to send to the pump.
    """
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    pump_addr = pump_letter_to_address(pump)
    full_command = f"/{pump_addr}{command}\r"
    print(f"Send: {pump}<-{full_command}")
    
    ser.write(full_command.encode())
    ser.flush()
    time.sleep(0.1)  # Small delay to ensure command is sent
    response = read_response(ser)
    print(f"Send: {pump}->{response}")

def stop_command(ser, pump="A"):
    """Send the stop command to a specific pump.
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump : str
            The pump address (e.g., 'A' for Pump A).
    """
    pump_addr = pump_letter_to_address(pump)
    full_command = f"/{pump_addr}T\r"
    print(f"Stop: {pump}<-{full_command}")
    
    ser.write(full_command.encode())
    ser.flush()
    time.sleep(0.1)  # Small delay to ensure command is sent
    response = read_response(ser).strip()
    print(f"Stop: {pump}->{response}")

# Command that runs a specific pump
def run_pump(ser, pump="A", eeprom_addr=None, command="R"):
    """Run a specific pump with send command or store and execute (if eeprom is set).
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump : str
            The pump address (e.g., 'A' for Pump A).
        eeprom_addr : str
            The EEPROM address (e.g., 's0' for EEPROM 0).
        command : str
            The command string to send to the pump.
        run_command : str
            The run command string to send to the pump.
    """

    pump_addr = pump_letter_to_address(pump)
    if eeprom_addr is None:
        send_command(ser, pump, command)
    else:
        store_command(ser, pump, eeprom_addr, command)
        execute_command(ser, pump, eeprom_addr) 

# Listen to responses from the pump
def read_response(ser, timeout=60):
    """Read the response from the pump.
    Arguments:
        ser : serial.Serial
            The serial connection object.
        timeout : float
            The timeout in seconds.
    Returns:
        str
            The response string from the pump.
    """
    # Ensure that it reads untill ETX (End of Text) character
    ETX = b'\x03'

    response = bytearray()
    t0 = time.time()

    while True:
        if time.time() - t0 > timeout:
            raise TimeoutError(f"Timed out waiting for ETX. Got: {bytes(response)!r}")

        b = ser.read(1)   # read exactly 1 byte
        if not b:
            continue

        response += b

        if b == ETX:
            break
    
    # Decodes the response bytes to string

    response_string = response.decode()

    return response_string


def stop_pump(ser, pump="A"):
    """Wrapper for the stop command.
    
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump : str
            The pump to stop (e.g., 'A' or 'B').

    """
    if pump not in ["A", "B"]:
        raise ValueError("Invalid pump selection. Choose 'A' or 'B'.")

    stop_command(ser, pump)
    
def input_command():
    """Prompt the user to input a command for the pump.
    Returns:
        str
            The command string entered by the user.
    """
    command = input("Enter the command to send to the pump: ")
    return command.strip()


# Pump Initialization
# Continuous flow start
# Complete stop

# Test
command_A = "J7ZV6000IA24000OV3000j10000A0IV6000A24000gJ7H0OV3000j10000A0IV6000A24000GR"
command_B = "J7ZV6000IA24000gJ7H0OV3000j10000A0IV6000A24000GR"
port = 'COM9'
ser = connect(port=port)


print("Starting pumps...")


command = input_command()

while command != "exit":
    
    run_pump(ser, pump="A", eeprom_addr=0, command=command)
    command = input_command()


disconnect(ser)