# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Luiz Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

import serial
import time

PUMP_ADDR = {"A": 1, "B": 2}
ETX = b'\x03'

# --- Connection ---

def connect(port, baudrate=9600, timeout=1):
    ser = serial.Serial(port, baudrate,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=timeout)
    time.sleep(2)
    return ser

def disconnect(ser):
    ser.close()

# --- Helpers ---

def pump_letter_to_address(pump: str) -> int:
    """Return numeric address for pump letter 'A' or 'B'."""
    if pump not in PUMP_ADDR:
        raise ValueError("Invalid pump selection. Choose 'A' or 'B'.")
    return PUMP_ADDR[pump]

def _flush(ser):
    """Clear buffers, write command, and wait briefly."""
    ser.reset_input_buffer()
    ser.reset_output_buffer()

def _send(ser, full_command: str):
    """Write a command string to the serial port."""
    ser.write(full_command.encode('utf-8'))
    ser.flush()
    time.sleep(0.1)

def read_response(ser, timeout=60) -> str:
    """Read bytes from pump until ETX character, then return as string."""
    response = bytearray()
    t0 = time.time()
    while True:
        if time.time() - t0 > timeout:
            raise TimeoutError(f"Timed out waiting for ETX. Got: {bytes(response)!r}")
        b = ser.read(1)
        if b:
            response += b
            if b == ETX:
                break
    return response.decode()

def input_command() -> str:
    """Prompt user to enter a pump command."""
    return input("Enter the command to send to the pump: ").strip()

# --- Core Command Functions ---

def compose_command(pump_addr: int = 1, eeprom_addr: int = None, command: str = "&") -> str:
    """Build a command string: /{pump_addr}{eeprom_addr}{command}\\r"""
    return f"/{pump_addr}{eeprom_addr}{command}\r"

def send_command(ser, pump="A", command="&"):
    """Send a direct command to a pump (no EEPROM)."""
    addr = pump_letter_to_address(pump)
    cmd = f"/{addr}{command}\r"
    _flush(ser)
    print(f"Send: {pump} <- {cmd}")
    _send(ser, cmd)
    print(f"Send: {pump} -> {read_response(ser)}")

def store_command(ser, pump="A", eeprom_addr=0, command="&"):
    """Store a command in the pump's EEPROM at the given address."""
    addr = pump_letter_to_address(pump)
    cmd = f"/{addr}s{eeprom_addr}{command}\r"
    _flush(ser)
    print(f"Store: {pump} <- {cmd}")
    _send(ser, cmd)
    print(f"Store: {pump} -> {read_response(ser)}")

def execute_command(ser, pump="A", eeprom_addr=0):
    """Execute a command stored in the pump's EEPROM."""
    addr = pump_letter_to_address(pump)
    cmd = f"/{addr}e{eeprom_addr}R\r"
    _flush(ser)
    print(f"Exec: {pump} <- {cmd}")
    _send(ser, cmd)
    print(f"Exec: {pump} -> {read_response(ser)}")

def stop_command(ser, pump="A"):
    """Send the stop (T) command to a pump."""
    addr = pump_letter_to_address(pump)
    cmd = f"/{addr}T\r"
    _flush(ser)
    print(f"Stop: {pump} <- {cmd}")
    _send(ser, cmd)
    print(f"Stop: {pump} -> {read_response(ser).strip()}")

def run_pump(ser, pump="A", eeprom_addr=None, command="R"):
    """Run a pump directly or via EEPROM store+execute if eeprom_addr is set."""
    if eeprom_addr is None:
        send_command(ser, pump, command)
    else:
        store_command(ser, pump, eeprom_addr, command)
        execute_command(ser, pump, eeprom_addr)

# --- Status Checks ---

def check_status(ser, pump) -> str:
    """Query and print current pump status."""
    addr = pump_letter_to_address(pump)
    cmd = f"/{addr}?\r"
    ser.write(cmd.encode())
    response = read_response(ser)
    print(f"Status of pump {pump}: {response}")
    return response

def is_running(ser, pump="A") -> bool:
    """Return True if pump is currently running (response contains '@')."""
    addr = pump_letter_to_address(pump)
    _flush(ser)
    _send(ser, f"/{addr}?\r")
    running = "@" in read_response(ser)
    print(f"Pump {pump} is {'running' if running else 'not running'}.")
    return running

def is_initialized(ser, pump="A") -> bool:
    """Return True if the pump is initialized (response contains '`1')."""
    addr = pump_letter_to_address(pump)
    _flush(ser)
    _send(ser, f"/{addr}?19\r")
    response = read_response(ser)
    initialized = "`1" in response
    print(f"Pump {pump} is {'initialized' if initialized else 'not initialized'}. Response: {response}")
    return initialized

def is_valve_output(ser, pump="A") -> bool:
    """Return True if pump valve is in output position (response contains 'o')."""
    addr = pump_letter_to_address(pump)
    _flush(ser)
    _send(ser, f"/{addr}?6\r")
    response = read_response(ser)
    output = "o" in response
    print(f"Pump {pump} valve output is {'enabled' if output else 'disabled'}. Response: {response}")
    return output

# --- High-Level Control ---

def initialize_pump(ser, pump="A", eeprom_addr=None, command="N2YZR"):
    """Initialize a pump. Default command sets high-resolution mode with right valve output."""
    print(f"Initializing pump {pump}...")
    run_pump(ser, pump=pump, eeprom_addr=eeprom_addr, command=command)

def check_until_initialized(ser, pump="A"):
    """Poll pump every 5 seconds until it reports initialized."""
    addr = pump_letter_to_address(pump)
    while True:
        _flush(ser)
        _send(ser, f"/{addr}?19\r")
        response = read_response(ser)
        if "`1" in response:
            print(f"Pump {pump} initialized. Response: {response}")
            break
        print(f"Waiting for pump {pump} to initialize... Response: {response}")
        time.sleep(5)

def stop_pump(ser, pump="A"):
    """Stop the specified pump."""
    print(f"Stopping pump {pump}...")
    stop_command(ser, pump)

def run_continuous_flow(ser, pump="A", eeprom_addr=None, command="R"):
    """Start continuous flow on a pump."""
    print(f"Starting continuous flow on pump {pump}...")
    run_pump(ser, pump=pump, eeprom_addr=eeprom_addr, command=command)

# --- Command Composers ---

def _validate_speeds(aspirate_speed, dispense_speed):
    if aspirate_speed < dispense_speed * 2:
        raise ValueError("Aspirate speed must be at least twice the dispense speed.")

def compose_command_continuous_flow_A(resolution=2, initial_speed=26000, aspirate_speed=None,
                                      dispense_speed=1000, initial_count=0,
                                      final_count=192000, j_value=1000) -> str:
    """Build a continuous-flow command string for Pump A."""
    if aspirate_speed is None:
        aspirate_speed = dispense_speed * 2
    _validate_speeds(aspirate_speed, dispense_speed)
    return (f"N{resolution}J7V{initial_speed}IA{final_count}OV{dispense_speed}"
            f"j{j_value}0A{initial_count}IV{aspirate_speed}A{final_count}"
            f"gJ7H0OV{dispense_speed}j{j_value}0A{initial_count}IV{aspirate_speed}A{final_count}GR")

def compose_command_continuous_flow_B(resolution=2, initial_speed=26000, aspirate_speed=None,
                                      dispense_speed=1000, initial_count=0,
                                      final_count=192000, j_value=1000) -> str:
    """Build a continuous-flow command string for Pump B."""
    if aspirate_speed is None:
        aspirate_speed = dispense_speed * 2
    _validate_speeds(aspirate_speed, dispense_speed)
    return (f"N{resolution}J7V{initial_speed}IA{final_count}"
            f"gJ7H0OV{dispense_speed}j{j_value}0A{initial_count}IV{aspirate_speed}A{final_count}GR")

# --- Testing ---

def send_DT(ser):
    """Send a firmware query command and print the raw response. For testing only."""
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    cmd = b"/1&\r"
    print("TX bytes:", cmd)
    ser.write(cmd)
    ser.flush()
    time.sleep(0.2)
    n = ser.in_waiting
    print("Bytes waiting:", n)
    print("RX raw bytes:", ser.read(n) if n > 0 else "No response")

def test_tricontinental_pump():
    """End-to-end test: initialize, run continuous flow for 10s, then stop both pumps."""
    port = 'COM9'
    cmd_a = compose_command_continuous_flow_A(resolution=0, aspirate_speed=6000,
                                              dispense_speed=3000, final_count=24000)
    cmd_b = compose_command_continuous_flow_B(resolution=0, aspirate_speed=6000,
                                              dispense_speed=3000, final_count=24000)

    ser = connect(port=port)

    for pump in ("A", "B"):
        if not is_initialized(ser, pump):
            initialize_pump(ser, pump)
    for pump in ("A", "B"):
        check_until_initialized(ser, pump)

    run_continuous_flow(ser, pump="A", command=cmd_a)
    run_continuous_flow(ser, pump="B", command=cmd_b)

    for pump in ("A", "B"):
        check_status(ser, pump)
        is_running(ser, pump)
        is_valve_output(ser, pump)

    while not (is_valve_output(ser, "A") and is_valve_output(ser, "B")):
        print("Waiting for valve output...")
        time.sleep(1)

    time.sleep(10)

    for pump in ("A", "B"):
        stop_pump(ser, pump)
        check_status(ser, pump)
        is_running(ser, pump)

    disconnect(ser)