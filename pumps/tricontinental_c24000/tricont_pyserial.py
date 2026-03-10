# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Luiz Albuquerque are acknowledged.
# All rights reserved.
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
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
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
    print(f"Stopping pump {pump}...")
    stop_command(ser, pump)
    
def input_command():
    """Prompt the user to input a command for the pump.
    Returns:
        str
            The command string entered by the user.
    """
    command = input("Enter the command to send to the pump: ")
    return command.strip()

def is_initialized(ser, pump="A"):
    """Check if the specified pump is initialized.
    
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump : str
            The pump to check (e.g., 'A' or 'B').
    Returns:
        bool
            True if the pump is initialized, False otherwise.
    """
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    pump_addr = pump_letter_to_address(pump)
    status_initialization_cmd = "?19"

    full_command = f"/{pump_addr}{status_initialization_cmd}\r" 
    ser.write(full_command.encode())
    ser.flush()
    time.sleep(0.1)  # Small delay to ensure command is sent
    response = read_response(ser)
    if "`1" in response:
        print(f"Pump {pump} is initialized.")
        print(f"Response: {response}")
        return True
    else:
        print(f"Pump {pump} is not initialized.")
        print(f"Response: {response}")
        return False
    
def initialize_pump(ser, pump="A", eeprom_addr=None, command="N2YZR"):
    """Initialize the specified pump with the given command.
    
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump : str
            The pump to initialize (e.g., 'A' or 'B').
        eeprom_addr : str
            The EEPROM address (e.g., 's0' for EEPROM 0).
        command : str
            The command string to send to the pump. Z initializes the pump with
            the right valve as the output. Y initializes the pump with the left 
            valve as the output.
        The N2YZR command initializes the pump in the high resolution
         mode (192000 counts) and the left valve as the output. Then it changes the 
         output valve to the right one.
    """
    print(f"Initializing pump {pump}...")
    run_pump(ser, pump=pump, eeprom_addr=eeprom_addr, command=command)
    
def check_until_initialized(ser, pump="A"):
    """Keep checking the status untill the specified pump is initialized.
    
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump : str
            The pump to check (e.g., 'A' or 'B').
    Returns:
        bool
            True if the pump is initialized, False otherwise.
    """
    pump_addr = pump_letter_to_address(pump)
    status_initialization_cmd = "?19"

    is_initialized = False
    # Query pump untill initialized
    while not is_initialized:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        full_command = f"/{pump_addr}{status_initialization_cmd}\r" 
        ser.write(full_command.encode())
        ser.flush()
        time.sleep(0.1)  # Small delay to ensure command is sent
        response = read_response(ser)
        if "`1" in response:
            is_initialized = True
            print(f"Pump {pump} initialized successfully.")
            print(f"Response: {response}")
        else:
            print(f"Waiting for pump {pump} to initialize...")
            print(f"Response: {response}")
            time.sleep(5)

def run_continuous_flow(ser, pump="A", eeprom_addr=None, command="R"):
    """Start continuous flow on the specified pump at the given rate.
    
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump : str
            The pump to run (e.g., 'A' or 'B').
        eeprom_addr : str
            The EEPROM address (e.g., 's0' for EEPROM 0).
        command : str
            The command string to send to the pump.
    """
    print(f"Starting continuous flow on pump {pump}...")
    run_pump(ser, pump=pump, eeprom_addr=eeprom_addr, command=command)

def compose_command_continuous_flow_A(resolution = 2,
                                      initial_speed = 26000,
                                      aspirate_speed = None,
                                        dispense_speed = 1000,
                                        initial_count = 0,
                                        final_count = 192000,
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
    
    command = f"N{resolution}J7V{initial_speed}IA{final_count}OV{dispense_speed}j{j_value}0A{initial_count}IV{aspirate_speed}A{final_count}gJ7H0OV{dispense_speed}j{j_value}0A{initial_count}IV{aspirate_speed}A{final_count}GR"
    
    return command

def compose_command_continuous_flow_B(resolution = 2,
                                      initial_speed = 26000,
                                      aspirate_speed = None,
                                      dispense_speed = 1000, 
                                      initial_count = 0, 
                                      final_count = 192000, 
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
    
    command = f"N{resolution}J7V{initial_speed}IA{final_count}gJ7H0OV{dispense_speed}j{j_value}0A{initial_count}IV{aspirate_speed}A{final_count}GR"
    
    return command
   

def check_status(ser, pump)-> str:
    """Check the status of the specified pump.
    
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump : str
            The pump to check (e.g., 'A' or 'B').
    Returns:
        str
            The status response from the pump.
    """
    pump_addr = pump_letter_to_address(pump)
    status_cmd = "?"

    full_command = f"/{pump_addr}{status_cmd}\r" 
    ser.write(full_command.encode())
    response = read_response(ser)
    print(f"Status of pump {pump}: {response}")
    
    return response

def is_running(ser, pump="A"):
    """Check if the specified pump is running.
    
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump : str
            The pump to check (e.g., 'A' or 'B').   
    Returns:
        bool
            True if the pump is running, False otherwise.
    """
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    pump_addr = pump_letter_to_address(pump)
    status_running_cmd = "?"

    full_command = f"/{pump_addr}{status_running_cmd}\r" 
    ser.write(full_command.encode())
    ser.flush()
    time.sleep(0.1)  # Small delay to ensure command is sent
    response = read_response(ser)
    if "@" in response:
        print(f"Pump {pump} is running.")
        return True
    else:
        print(f"Pump {pump} is not running.")
        return False
# ------------------------------------------------------------------------------
# Example usage of the above functions
# Continuous flow start
# Complete stop
def is_valve_output(ser, pump="A"):
    """Check if the valve output of the specified pump is enabled.
    
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump : str
            The pump to check (e.g., 'A' or 'B').
    Returns:
        str
            The valve position response from the pump.
    """
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    pump_addr = pump_letter_to_address(pump)
    valve_position_cmd = "?6"

    full_command = f"/{pump_addr}{valve_position_cmd}\r" 
    ser.write(full_command.encode())
    ser.flush()
    time.sleep(0.1)  # Small delay to ensure command is sent
    response = read_response(ser)

    print(f"Valve position response for pump {pump}: {response}")
    if "o" in response:
        print(f"Pump {pump} valve output is enabled.")
        output_vale = True
    else:
        print(f"Pump {pump} valve output is disabled.")
        output_vale = False

    return output_vale

def test_tricontinental_pump():
    """Test the Tricontinental C24000 pump control functions."""
    # Connect to the pump
    port = 'COM9'
    
    # Test
    composed_cmd_a = compose_command_continuous_flow_A(resolution=0,
                                                        aspirate_speed=6000,
                                                        dispense_speed=3000,
                                                        initial_count=0,
                                                        final_count=24000,
                                                        j_value=1000)
    composed_cmd_b = compose_command_continuous_flow_B(resolution=0,
                                                        aspirate_speed=6000,    
                                                        dispense_speed=3000,
                                                        initial_count=0,
                                                        final_count=24000,
                                                        j_value=1000)
    
    ser = connect(port=port)

    print("Checking initialization status...")
    init_a = is_initialized(ser, pump="A")
    init_b = is_initialized(ser, pump="B")

    if not init_a:
        print("Initializing pump A...")
        initialize_pump(ser, pump="A")
    if not init_b:
        print("Initializing pump B...")
        initialize_pump(ser, pump="B")
    print("Ensuring pumps are initialized...")
    check_until_initialized(ser, pump="A")
    check_until_initialized(ser, pump="B")
    print("Pumps are initialized.")

    print("Starting continuous flow on pumps...")
    run_continuous_flow(ser, pump="A", command=composed_cmd_a)
    run_continuous_flow(ser, pump="B", command=composed_cmd_b)
    check_status(ser, pump="A")
    check_status(ser, pump="B")
    is_running(ser, pump="A")
    is_running(ser, pump="B")
    is_valve_output(ser, pump="A")
    is_valve_output(ser, pump="B")

    while not is_valve_output(ser, pump="A") or not is_valve_output(ser, pump="B"):
        print("Waiting for valve output to be enabled...")
        time.sleep(1)

    time.sleep(10)  # Let the pumps run for 10 seconds
    print("Stopping pumps...")
    stop_pump(ser, pump="A")
    stop_pump(ser, pump="B")
    check_status(ser, pump="A")
    check_status(ser, pump="B")
    is_running(ser, pump="A")
    is_running(ser, pump="B")
    disconnect(ser)

