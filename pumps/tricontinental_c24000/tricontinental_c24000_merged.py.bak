# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Luiz Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

import serial
import time
import sys
from pathlib import Path

# Add the project root to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from pumps.pumps import Pump

# ==============================================================================
# Serial / Low-Level Helpers
# ==============================================================================

PUMP_ADDR = {"A": 1, "B": 2}
ETX = b'\x03'  # End-of-Text byte — the pump appends this to every response


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


def pump_letter_to_address(pump: str) -> int:
    """Return the numeric address for pump letter 'A' or 'B'."""
    if pump not in PUMP_ADDR:
        raise ValueError("Invalid pump selection. Choose 'A' or 'B'.")
    return PUMP_ADDR[pump]


def _flush(ser):
    """Clear serial input/output buffers before sending a new command."""
    ser.reset_input_buffer()
    ser.reset_output_buffer()


def _send(ser, cmd: str):
    """Encode and write a command string to the serial port."""
    ser.write(cmd.encode('utf-8'))
    ser.flush()
    time.sleep(0.1)


def read_response(ser, timeout=60) -> str:
    """Read bytes from the pump until the ETX (End-of-Text) byte, then return as string.
    
    The Tricontinental pump terminates every response with an ETX byte (0x03).
    We read one byte at a time until we see it, then decode the full response.
    """
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


# ==============================================================================
# Core Pump Commands
# ==============================================================================

def send_command(ser, pump: str, command: str):
    """Send a direct command to a pump (no EEPROM involved)."""
    addr = pump_letter_to_address(pump)
    cmd = f"/{addr}{command}\r"  # All pump commands follow the format: /{address}{command}\r
    _flush(ser)
    print(f"Send: {pump} <- {cmd}")
    _send(ser, cmd)
    print(f"Send: {pump} -> {read_response(ser)}")


def store_command(ser, pump: str, eeprom_addr: int, command="&"):
    """Store a command in the pump's EEPROM at the given address.
    
    EEPROM is a small non-volatile memory chip on the pump. Storing a command
    there lets you trigger it later with execute_command without resending the
    full command string over serial — useful for long or repeated sequences.
    The 's' prefix tells the pump this is a store operation.
    """
    addr = pump_letter_to_address(pump)
    cmd = f"/{addr}s{eeprom_addr}{command}\r"
    _flush(ser)
    print(f"Store: {pump} <- {command} at EEPROM {eeprom_addr}")
    _send(ser, cmd)
    print(f"Store: {pump} -> {read_response(ser)}")


def execute_command(ser, pump: str, eeprom_addr: int):
    """Retrieve and execute a command previously stored in EEPROM.
    
    The 'e' prefix tells the pump to look up the command at that EEPROM address.
    The trailing 'R' is the Run instruction — without it the pump loads but doesn't start.
    """
    addr = pump_letter_to_address(pump)
    cmd = f"/{addr}e{eeprom_addr}R\r"  # 'R' = Run; required to actually start execution
    _flush(ser)
    print(f"Execute: {pump} <- EEPROM {eeprom_addr}")
    _send(ser, cmd)
    print(f"Execute: {pump} -> {read_response(ser)}")


def stop_command(ser, pump: str):
    """Send the terminate (T) command to immediately stop a pump."""
    addr = pump_letter_to_address(pump)
    cmd = f"/{addr}T\r"
    _flush(ser)
    print(f"Stop: {pump} <- {cmd}")
    _send(ser, cmd)
    print(f"Stop: {pump} -> {read_response(ser).strip()}")


def run_pump(ser, pump: str, eeprom_addr: int = None, command="R"):
    """Run a pump by sending a command directly, or via EEPROM if eeprom_addr is set.
    
    - If eeprom_addr is None: sends the command directly over serial (simpler, one-shot).
    - If eeprom_addr is set: stores the command in EEPROM first, then executes it.
      Use the EEPROM path for complex sequences you want to reuse or run reliably
      without sending large command strings repeatedly.
    'R' on its own is the Run command — it tells the pump to start executing
    whatever was last loaded.
    """
    if eeprom_addr is None:
        send_command(ser, pump, command)
    else:
        store_command(ser, pump, eeprom_addr, command)
        execute_command(ser, pump, eeprom_addr)


# ==============================================================================
# Status Checks
# ==============================================================================

def check_status(ser, pump: str) -> str:
    """Query and return the current pump status string."""
    addr = pump_letter_to_address(pump)
    ser.write(f"/{addr}?\r".encode("utf-8"))
    response = read_response(ser)
    print(f"Status of pump {pump}: {response}")
    return response


def is_running(ser, pump: str) -> bool:
    """Return True if the pump is currently running.
    
    The Tricontinental protocol wraps status responses with status characters
    defined in the firmware: '@' means the pump is busy/running, '`' means idle.
    These are fixed by the manufacturer and cannot be changed in settings.
    """
    addr = pump_letter_to_address(pump)
    _flush(ser)
    _send(ser, f"/{addr}?\r")
    running = "@" in read_response(ser)
    print(f"Pump {pump} is {'running' if running else 'not running'}.")
    return running


def is_initialized(ser, pump: str) -> bool:
    """Return True if the pump has completed its initialization routine.
    
    '?19' queries register 19, which holds the initialization status.
    Register numbers are fixed by the pump firmware and cannot be reassigned.
    The response contains '`1' when initialized, '`0' when not.
    """
    addr = pump_letter_to_address(pump)
    _flush(ser)
    _send(ser, f"/{addr}?19\r")
    response = read_response(ser)
    initialized = "`1" in response
    print(f"Pump {pump} is {'initialized' if initialized else 'not initialized'}. Response: {response}")
    return initialized


def is_valve_output(ser, pump: str) -> bool:
    """Return True if the valve is currently in the output (dispense) position.
    
    '?6' queries register 6, which holds the valve position state.
    Like all register numbers, this is defined by the pump firmware.
    The response contains 'o' for output position, 'i' for input (aspirate) position.
    """
    addr = pump_letter_to_address(pump)
    _flush(ser)
    _send(ser, f"/{addr}?6\r")
    response = read_response(ser)
    valve_output = "o" in response
    print(f"Pump {pump} valve is {'in output position' if valve_output else 'not in output position'}. Response: {response}")
    return valve_output


# ==============================================================================
# High-Level Control
# ==============================================================================

def initialize_pump(ser, pump: str, eeprom_addr: int = None, command="N2YZR"):
    """Initialize the pump.
    
    Default command 'N2YZR' means:
      N2 = high-resolution mode (192,000 counts full stroke)
      Y  = initialize with left valve as output
      Z  = initialize with right valve as output
      R  = Run
    """
    print(f"Initializing pump {pump}...")
    run_pump(ser, pump=pump, eeprom_addr=eeprom_addr, command=command)


def check_until_initialized(ser, pump: str):
    """Poll the pump every 5 seconds until it reports initialized."""
    addr = pump_letter_to_address(pump)
    while True:
        _flush(ser)
        _send(ser, f"/{addr}?19\r")
        response = read_response(ser)
        if "`1" in response:
            print(f"Pump {pump} is initialized. Response: {response}")
            break
        print(f"Pump {pump} not initialized yet. Response: {response}")
        time.sleep(5)


def stop_pump(ser, pump: str):
    """Stop the specified pump."""
    print(f"Stopping pump {pump}...")
    stop_command(ser, pump)


def run_continuous_flow(ser, pump: str, command: str):
    """Start continuous flow on a pump using the given pre-composed command string."""
    print(f"Starting continuous flow on pump {pump}...")
    run_pump(ser, pump=pump, eeprom_addr=None, command=command)


# ==============================================================================
# Command Composers
# ==============================================================================

def _validate_speeds(aspirate_speed, dispense_speed):
    """Ensure aspirate speed is at least 2x dispense speed.
    
    This pump runs two syringes alternately: while one dispenses, the other
    refills (aspirates). The aspirating syringe must finish refilling before
    the dispensing one empties, or there will be a gap in flow. At 2x speed
    the aspirate cycle completes in exactly half the time, guaranteeing
    seamless handoff with no dead time.
    """
    if aspirate_speed < dispense_speed * 2:
        raise ValueError("Aspirate speed must be at least 2x the dispense speed.")


def compose_command_continuous_flow_A(resolution=2, initial_speed=26000, aspirate_speed=None,
                                      dispense_speed=1000, initial_count=0,
                                      final_count=192000, j_value=1000) -> str:
    """Build a continuous-flow command string for Pump A.
    
    Pump A performs a full prime cycle before entering the main dispense loop,
    hence the longer command sequence vs Pump B.
    """
    if aspirate_speed is None:
        aspirate_speed = dispense_speed * 2
    _validate_speeds(aspirate_speed, dispense_speed)
    return (f"N{resolution}J7V{initial_speed}IA{final_count}OV{dispense_speed}"
            f"j{j_value}0A{initial_count}IV{aspirate_speed}A{final_count}"
            f"gJ7H0OV{dispense_speed}j{j_value}0A{initial_count}IV{aspirate_speed}A{final_count}GR")


def compose_command_continuous_flow_B(resolution=2, initial_speed=26000, aspirate_speed=None,
                                      dispense_speed=1000, initial_count=0,
                                      final_count=192000, j_value=1000) -> str:
    """Build a continuous-flow command string for Pump B.
    
    Pump B skips the initial prime and jumps straight into the dispense loop,
    so it starts offset from Pump A to maintain continuous alternating flow.
    """
    if aspirate_speed is None:
        aspirate_speed = dispense_speed * 2
    _validate_speeds(aspirate_speed, dispense_speed)
    return (f"N{resolution}J7V{initial_speed}IA{final_count}"
            f"gJ7H0OV{dispense_speed}j{j_value}0A{initial_count}IV{aspirate_speed}A{final_count}GR")


# ==============================================================================
# TricontinentalC24000 Pump Class
# ==============================================================================

class TricontinentalC24000(Pump):
    """Driver for Tricontinental C24000 dual-syringe pump.

    Converts flow rate and volume to device counts, runs both syringes
    for a calculated duration, then stops.
    """

    # Calibration values for 1 mL syringe: 196.82 counts/µL (0.005107 µL/count)
    # TODO: Populate with actual calibration data for your specific pump
    CALIBRATION_VALUES = {flowrate: 196.82 for flowrate in (100, 200, 500, 1000, 1500, 2000)}
    DEFAULT_COUNTS_PER_UL = 196.82

    def __init__(self, port: str, baudrate: int = 9600, name: str = "Tricontinental_C24000"):
        self.port = port
        self.baudrate = baudrate
        self.name = name
        self.serial = None
        self._connected = False
        self.uL_per_count = 0.005107
        self.counts_per_uL = 1 / self.uL_per_count
        self.flow_rate_ul_min = 0.0
        self.flow_rate_ul_sec = 0.0

    def connect(self) -> None:
        """Open serial connection and initialize both pumps if needed.
        
        This method handles connection AND initialization together as a convenience —
        callers only need one call to get the pump fully ready to use.
        """
        try:
            self.serial = connect(port=self.port, baudrate=self.baudrate)
            time.sleep(2)

            # Drain any leftover startup bytes so they don't corrupt the first response
            startup = b""
            while self.serial.in_waiting:
                startup += self.serial.read(self.serial.in_waiting)
                time.sleep(0.1)
            if startup:
                print(f"{self.name}: Cleared {len(startup)} bytes of startup data")

            self._connected = True
            print(f"{self.name}: Connected on {self.port}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.name}: {e}")

        for pump in ("A", "B"):
            initialized = is_initialized(self.serial, pump)
            if initialized is None:
                raise RuntimeError(f"{self.name}: Could not get init status. Are pumps connected?")
            if not initialized:
                print(f"{self.name}: Initializing pump {pump}...")
                initialize_pump(self.serial, pump=pump)

        for pump in ("A", "B"):
            check_until_initialized(self.serial, pump=pump)
        print(f"{self.name}: Both pumps initialized and ready.")

    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Dispense a specified volume at the given flow rate on both pumps."""
        if not self._connected:
            raise RuntimeError(f"{self.name}: Not connected.")
        if flow_rate_ul_min <= 0:
            raise ValueError(f"Flow rate must be > 0, got {flow_rate_ul_min}")
        if volume_ul <= 0:
            raise ValueError(f"Volume must be > 0, got {volume_ul}")

        self.flow_rate_ul_min = abs(flow_rate_ul_min)
        self.flow_rate_ul_sec = self.flow_rate_ul_min / 60.0
        self.counts_per_uL = self.CALIBRATION_VALUES.get(int(self.flow_rate_ul_min), self.DEFAULT_COUNTS_PER_UL)

        pump_time_sec, total_wait_time = self._calculate_pump_time(volume_ul, self.flow_rate_ul_min)
        print(f"{self.name}: Dispensing {volume_ul} µL at {flow_rate_ul_min} µL/min")
        print(f"{self.name}: Pump time: {pump_time_sec:.2f}s, total wait: {total_wait_time:.2f}s")

        # Drain any stale bytes from the buffer so they don't corrupt the next read,
        # then stop any ongoing operation before starting a fresh dispense.
        if self.serial.in_waiting:
            self.serial.read(self.serial.in_waiting)
        self.stop()
        self.serial.flush()
        time.sleep(2)

        speed = self._convert_flow_rate(flow_rate_ul_min)
        run_continuous_flow(self.serial, pump="A",
                            command=compose_command_continuous_flow_A(dispense_speed=speed))
        run_continuous_flow(self.serial, pump="B",
                            command=compose_command_continuous_flow_B(dispense_speed=speed))

        time.sleep(1)
        while not (is_valve_output(self.serial, "A") and is_valve_output(self.serial, "B")):
            print(f"{self.name}: Waiting for pumps to start dispensing...")
            time.sleep(0.5)

        start = time.time()
        while time.time() - start < pump_time_sec:
            print(f"{self.name}: Dispensing... {time.time() - start:.2f}/{pump_time_sec:.2f}s")
            time.sleep(60)

        self.stop()
        print(f"{self.name}: Dispense complete — {volume_ul} µL dispensed")

    def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Not implemented on this pump model."""
        print(f"{self.name}: Aspirate is not supported on this pump.")

    def set_flow_rate(self, flow_rate_ul_min: float) -> None:
        """Store the flow rate; applied on the next dispense() call."""
        if flow_rate_ul_min <= 0:
            raise ValueError(f"Flow rate must be > 0, got {flow_rate_ul_min}")
        if type(flow_rate_ul_min) is not (int, float):
            raise ValueError(f"Flow rate must be a numeric value, got {type(flow_rate_ul_min).__name__}") 
        self.flow_rate_ul_min = abs(flow_rate_ul_min)

    def stop(self) -> None:
        """Stop both pumps."""
        if not self._connected or not self.serial or not self.serial.is_open:
            return
        for pump in ("A", "B"):
            try:
                stop_pump(self.serial, pump=pump)
                print(f"{self.name}: Stopped pump {pump}.")
                time.sleep(0.5)
            except Exception as e:
                print(f"{self.name}: Error stopping pump {pump}: {e}")

    def status(self) -> str:
        """Return a status string for both pumps."""
        if not self._connected:
            return f"{self.name}: Not connected."
        try:
            a = check_status(self.serial, "A")
            b = check_status(self.serial, "B")
            return f"{self.name}: Pump A: {a} | Pump B: {b}"
        except Exception as e:
            return f"{self.name}: Error checking status: {e}"

    def close(self) -> None:
        """Stop pumps and close the serial connection."""
        if self.serial and self.serial.is_open:
            try:
                self.stop()
            except Exception:
                pass
            self.serial.close()
            self._connected = False
            print(f"{self.name}: Closed.")

    # --- Private helpers ---

    def _convert_flow_rate(self, ul_min: float) -> int:
        """Convert flow rate in µL/min to device speed in counts/second."""
        counts_per_uL = self.CALIBRATION_VALUES.get(int(abs(ul_min)), self.DEFAULT_COUNTS_PER_UL)
        return int((abs(ul_min) / 60.0) * counts_per_uL)

    def _convert_volume_to_counts(self, volume_ul: float) -> int:
        """Convert volume in µL to device counts."""
        return int(abs(volume_ul) * self.counts_per_uL)

    def _calculate_pump_time(self, volume_ul: float, flow_rate_ul_min: float,
                              buffer_sec: float = 2.0) -> tuple:
        """Return (pump_time_sec, pump_time_sec + buffer_sec) for a given volume and flow rate."""
        if flow_rate_ul_min <= 0 or volume_ul <= 0:
            raise ValueError(f"Flow rate and volume must be > 0. "
                             f"Got flow_rate={flow_rate_ul_min}, volume={volume_ul}")
        pump_time = abs(volume_ul) / (abs(flow_rate_ul_min) / 60.0)
        return pump_time, pump_time + buffer_sec

    def get_pump_parameters(self) -> None:
        """Print current pump parameters."""
        print(f"Pump parameters for {self.name}:")
        print(f"  Flow rate:      {self.flow_rate_ul_min} µL/min ({self.flow_rate_ul_sec:.2f} µL/s)")
        print(f"  µL per count:   {self.uL_per_count}")   # BUG FIX: was printing counts_per_uL twice
        print(f"  Counts per µL:  {self.counts_per_uL:.4f}")
        print(f"  Connected:      {self._connected}")
        print(f"  Port:           {self.port} @ {self.baudrate} baud")


# ==============================================================================
# Testing
# ==============================================================================

def test_tricontinental_pump():
    """End-to-end test: initialize, run continuous flow for 10s, then stop both pumps."""
    port = 'COM17'
    cmd_a = compose_command_continuous_flow_A(
    resolution=0,
    initial_speed=5600,   # ← safe C24000 default per manual
    aspirate_speed=6000,
    dispense_speed=3000,
    final_count=24000
    )
    cmd_b = compose_command_continuous_flow_B(
    resolution=0,
    initial_speed=5600,   # ← was missing, same fix as Pump A
    aspirate_speed=6000,
    dispense_speed=3000,
    final_count=24000
    )

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
        print("Waiting for pumps to start dispensing...")
        time.sleep(1)

    time.sleep(10)

    for pump in ("A", "B"):
        stop_pump(ser, pump)
        check_status(ser, pump)
        is_running(ser, pump)

    disconnect(ser)

if __name__ == "__main__":
    test_tricontinental_pump()