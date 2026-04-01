# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Luiz Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

import serial
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from pumps.pumps import Pump

ETX = b'\x03'  # Pump appends this byte to every response


class TricontinentalC24000(Pump):
    """Driver for the Tricontinental C24000 dual-syringe peristaltic pump.

    Two pump heads (A=address 1, B=address 2) alternate strokes to produce
    continuous flow.  All communication uses direct serial commands — no EEPROM.
    Calibrated for a 1 mL syringe (196.82 counts/µL, 0.005107 µL/count).
    """

    COUNTS_PER_UL = 196.82  # 1 mL syringe calibration constant

    def __init__(self, port: str, baudrate: int = 9600,
                 name: str = "Tricontinental_C24000"):
        self.port = port
        self.baudrate = baudrate
        self.name = name
        self.serial = None
        self._connected = False
        self.flow_rate_ul_min = 0.0

    # -----------------------------------------------------------------------
    # Public API  (implements the Pump abstract base class)
    # -----------------------------------------------------------------------

    def connect(self) -> None:
        """Open serial connection and initialize both pump heads."""
        try:
            self.serial = serial.Serial(
                self.port, self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
            )
            time.sleep(2)
            # Drain startup chatter the firmware emits on power-on
            while self.serial.in_waiting:
                self.serial.read(self.serial.in_waiting)
                time.sleep(0.1)
            self._connected = True
            print(f"{self.name}: Connected on {self.port}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.name}: {e}")

        for addr in (1, 2):
            if not self._is_initialized(addr):
                print(f"{self.name}: Initializing pump {addr}...")
                self._initialize_pump(addr)
        for addr in (1, 2):
            self._wait_until_initialized(addr)
        print(f"{self.name}: Both pumps initialized and ready.")

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

    def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Not implemented on this pump model."""
        print(f"{self.name}: Aspirate is not supported on this pump.")

    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Dispense a volume at the given flow rate using both pump heads."""
        if not self._connected:
            raise RuntimeError(f"{self.name}: Not connected.")
        if flow_rate_ul_min <= 0:
            raise ValueError(f"Flow rate must be > 0, got {flow_rate_ul_min}")
        if volume_ul <= 0:
            raise ValueError(f"Volume must be > 0, got {volume_ul}")

        self.flow_rate_ul_min = abs(flow_rate_ul_min)
        pump_time_sec, _ = self._calculate_pump_time(volume_ul, self.flow_rate_ul_min)
        print(f"{self.name}: Dispensing {volume_ul} µL at {flow_rate_ul_min} µL/min "
              f"(~{pump_time_sec:.1f} s)")

        # Clear any stale bytes, then stop any running operation before starting fresh
        if self.serial.in_waiting:
            self.serial.read(self.serial.in_waiting)
        self.stop()
        self.serial.flush()
        time.sleep(2)

        speed = self._convert_flow_rate(flow_rate_ul_min)
        final_count = int(volume_ul * self.COUNTS_PER_UL)
        self._run_continuous_flow(1, self._build_command_pump_a(speed, final_count))
        self._run_continuous_flow(2, self._build_command_pump_b(speed, final_count))

        # Wait for both valves to switch into the dispense position
        time.sleep(1)
        while not (self._is_valve_output(1) and self._is_valve_output(2)):
            print(f"{self.name}: Waiting for pumps to start dispensing...")
            time.sleep(0.5)

        # Wait out the dispense; check every 60 s so long runs still log progress
        start = time.time()
        while True:
            elapsed = time.time() - start
            if elapsed >= pump_time_sec:
                break
            print(f"{self.name}: Dispensing... {elapsed:.1f}/{pump_time_sec:.1f} s")
            time.sleep(min(60.0, pump_time_sec - elapsed))

        self.stop()
        print(f"{self.name}: Dispense complete — {volume_ul} µL dispensed.")

    def set_flow_rate(self, flow_rate_ul_min: float) -> None:
        """Store the flow rate; it is applied on the next dispense() call."""
        self.flow_rate_ul_min = abs(flow_rate_ul_min)

    def stop(self) -> None:
        """Stop both pump heads."""
        if not self._connected or not self.serial or not self.serial.is_open:
            return
        for addr in (1, 2):
            try:
                self._stop_pump(addr)
                time.sleep(0.5)
            except Exception as e:
                print(f"{self.name}: Error stopping pump {addr}: {e}")

    def status(self) -> str:
        """Return a combined status string for both pump heads."""
        if not self._connected:
            return f"{self.name}: Not connected."
        try:
            a = self._check_status(1)
            b = self._check_status(2)
            return f"{self.name}: Pump A: {a} | Pump B: {b}"
        except Exception as e:
            return f"{self.name}: Error checking status: {e}"

    # -----------------------------------------------------------------------
    # Serial I/O
    # -----------------------------------------------------------------------

    def _send(self, cmd: str) -> None:
        """Flush buffers, then write a command string to the serial port."""
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        self.serial.write(cmd.encode('utf-8'))
        self.serial.flush()
        time.sleep(0.1)

    def _read_response(self, timeout: float = 60) -> str:
        """Read bytes until the ETX terminator (0x03), then decode to string."""
        response = bytearray()
        t0 = time.time()
        while True:
            if time.time() - t0 > timeout:
                raise TimeoutError(
                    f"Timed out waiting for pump response. Got: {bytes(response)!r}")
            b = self.serial.read(1)
            if b:
                response += b
                if b == ETX:
                    break
        return response.decode()

    def _send_command(self, pump_addr: int, command: str) -> str:
        """Send /{addr}{command}\\r to the pump and return the response."""
        self._send(f"/{pump_addr}{command}\r")
        return self._read_response()

    # -----------------------------------------------------------------------
    # Initialization helpers
    # -----------------------------------------------------------------------

    def _initialize_pump(self, pump_addr: int) -> None:
        """Send the initialization command sequence to one pump head.

        N2 = high-resolution mode (192,000 counts per full stroke)
        Y  = initialize left valve as output
        Z  = initialize right valve as output
        R  = Run
        """
        self._send_command(pump_addr, "N2YZR")

    def _wait_until_initialized(self, pump_addr: int) -> None:
        """Poll register 19 every 5 s until the pump reports initialized."""
        while True:
            self._send(f"/{pump_addr}?19\r")
            response = self._read_response()
            if "`1" in response:
                print(f"{self.name}: Pump {pump_addr} initialized.")
                break
            print(f"{self.name}: Pump {pump_addr} not ready yet, waiting...")
            time.sleep(5)

    # -----------------------------------------------------------------------
    # Status queries
    # -----------------------------------------------------------------------

    def _is_initialized(self, pump_addr: int) -> bool:
        """Return True if the pump head has completed initialization.

        Register 19 holds initialization status: '`1' = initialized, '`0' = not.
        """
        self._send(f"/{pump_addr}?19\r")
        return "`1" in self._read_response()

    def _is_valve_output(self, pump_addr: int) -> bool:
        """Return True if the valve is in dispense (output) position.

        Register 6 holds valve position: 'o' = output/dispense, 'i' = input/aspirate.
        """
        self._send(f"/{pump_addr}?6\r")
        return "o" in self._read_response()

    def _is_running(self, pump_addr: int) -> bool:
        """Return True if the pump head is currently running.

        '@' in the status response means busy/running; '`' means idle.
        """
        self._send(f"/{pump_addr}?\r")
        return "@" in self._read_response()

    def _stop_pump(self, pump_addr: int) -> None:
        """Send the terminate (T) command to one pump head."""
        print(f"{self.name}: Stopping pump {pump_addr}...")
        self._send_command(pump_addr, "T")

    def _check_status(self, pump_addr: int) -> str:
        """Return the raw status string from one pump head."""
        self._send(f"/{pump_addr}?\r")
        return self._read_response()

    # -----------------------------------------------------------------------
    # Math helpers
    # -----------------------------------------------------------------------

    def _convert_flow_rate(self, ul_min: float) -> int:
        """Convert µL/min to device speed in counts/second."""
        return int((abs(ul_min) / 60.0) * self.COUNTS_PER_UL)

    def _calculate_pump_time(self, volume_ul: float, flow_rate_ul_min: float,
                              buffer_sec: float = 2.0) -> tuple:
        """Return (pump_time_sec, pump_time_sec + buffer_sec)."""
        pump_time = abs(volume_ul) / (abs(flow_rate_ul_min) / 60.0)
        return pump_time, pump_time + buffer_sec

    # -----------------------------------------------------------------------
    # Command builders
    # -----------------------------------------------------------------------

    def _build_command_pump_a(self, speed: int, final_count: int,
                               resolution: int = 0,
                               initial_speed: int = 26000) -> str:
        """Build the continuous-flow command string for Pump A.

        Pump A performs a full prime stroke first, then enters the main
        dispense loop.  This ensures tubing is primed and both heads are
        offset so flow is continuous (no dead time at the handoff).

        Command tokens used:
          N{r}          resolution (0 = 24 000, 1 = 48 000, 2 = 192 000 counts/stroke)
          J7            define loop label 7
          V{n}I         set speed to n counts/s, switch valve to input
          A{n}          move plunger to absolute position n
          O             switch valve to output
          V{n}          set speed to n counts/s
          j{n}          repeat next block n times
          gJ7           go to label 7 (start of loop)
          H0            halt 0 ms (synchronisation point)
          G             go to programme start
          R             run
        """
        aspirate_speed = speed * 2  # must refill in half the dispense time
        j_value = 1000
        initial_count = 0
        return (
            f"N{resolution}J7V{initial_speed}IA{final_count}"
            f"OV{speed}j{j_value}0A{initial_count}IV{aspirate_speed}A{final_count}"
            f"gJ7H0OV{speed}j{j_value}0A{initial_count}IV{aspirate_speed}A{final_count}GR"
        )

    def _build_command_pump_b(self, speed: int, final_count: int,
                               resolution: int = 0,
                               initial_speed: int = 26000) -> str:
        """Build the continuous-flow command string for Pump B.

        Pump B skips the prime cycle and jumps straight into the loop,
        offset from Pump A so the two heads alternate seamlessly.
        """
        aspirate_speed = speed * 2
        j_value = 1000
        initial_count = 0
        return (
            f"N{resolution}J7V{initial_speed}IA{final_count}"
            f"gJ7H0OV{speed}j{j_value}0A{initial_count}IV{aspirate_speed}A{final_count}GR"
        )

    def _run_continuous_flow(self, pump_addr: int, command: str) -> None:
        """Send a pre-built continuous-flow command directly to a pump head."""
        print(f"{self.name}: Starting continuous flow on pump {pump_addr}...")
        self._send_command(pump_addr, command)
