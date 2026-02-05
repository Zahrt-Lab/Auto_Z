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

def send_DT(ser):
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
        
def send_command(ser, pump_addr, command):
    """Send a command to a specific pump.
    Pump A: addr =/1
    PumpB: addr =/2
    EEPROM address: s0 for Pump A, s1 for Pump B
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump_addr : str
            The address of the pump (e.g., '/1' for Pump A).
        eeprom_addr : str
            The EEPROM address of the pump (e.g., '0x01').
        command : str
            The command string to send to the pump.
    """
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    full_command = f"{pump_addr}{command}\r"
    print(f"Sending command: {full_command}")
    
    ser.write(full_command.encode())
    ser.flush()
    time.sleep(0.1)  # Small delay to ensure command is sent

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

def send_and_print(ser, pump_addr, command, timeout=60):
    """Send a command to the pump and print the response.
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump_addr : str
            The address of the pump (e.g., '/1' for Pump A).
        eeprom_addr : str
            The EEPROM address of the pump (e.g., '0x01').
        command : str
            The command string to send to the pump.
        timeout : float
            The timeout in seconds for reading the response.
    """
    send_command(ser, pump_addr, command)
    response = read_response(ser, timeout)
    print(f"Response: {response}")

def input_command():
    """Prompt the user to input a command for the pump.
    Returns:
        str
            The command string entered by the user.
    """
    command = input("Enter the command to send to the pump: ")
    return command.strip()

def stop_pump(ser, pump_addr):
    """Send the stop command to the pump.
    Arguments:
        ser : serial.Serial
            The serial connection object.
        pump_addr : str
            The address of the pump (e.g., '/1' for Pump A).
        eeprom_addr : str
            The EEPROM address of the pump .
    """
    stop_command = "T"  # T is the stop command
    send_and_print(ser, pump_addr, stop_command)

def main():
    # Example usage
    port = 'COM9'  # Change to your serial port
    pump_addr = '/1'  # Pump A

    ser = connect(port)
    print(f"Connected to the pump on COM {port}.")
    command = "s0ZR"
    run = "e0R"
    addr = "/1"

    try:
        send_command(ser, addr, command)
        response = read_response(ser)
        print(f"Response: {response}")
        send_command(ser, addr, run)
        response = read_response(ser)
        print(f"Response: {response}")
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        disconnect(ser)
def main_old():
    # Example usage
    port = 'COM9'  # Change to your serial port
    pump_addr = '/1'  # Pump A
    eeprom_addr = 's0'  # EEPROM address for Pump A

    ser = connect(port)
    print(f"Connected to the pump on COM {port}.")
    try:
        command=input_command()
        send_and_print(ser, pump_addr, eeprom_addr, command)
        while command != "exit":
            command = input_command()
            send_and_print(ser, pump_addr, eeprom_addr, command)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        disconnect(ser)

# Simple test

main()


# Pump Initialization
# Continuous flow start
# Complete stop