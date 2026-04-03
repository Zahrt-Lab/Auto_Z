# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Luiz Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

from pumps.pumps import Pump
from pumps.tricontinental_c24000 import tricont_pyserial as tri
import time

'''
Controls the Tricontinental C24000 dual syringe pump via serial interface.
'''


class TricontinentalC24000(Pump):
    """Driver for Tricontinental C24000 Dual Syringe Pump.

    Converts flow rate and volume to device counts, runs both syringes
    for a calculated duration, then stops.
    """

    # Calibration for 1 mL syringe: 196.82 counts/µL (0.005107 µL/count)
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
        """Open serial connection and initialize both pumps if needed."""
        try:
            self.serial = tri.connect(port=self.port, baudrate=self.baudrate)
            time.sleep(2)

            # Drain any startup bytes
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

        # Initialize pumps if not already done
        for pump in ("A", "B"):
            initialized = tri.is_initialized(self.serial, pump)
            if initialized is None:
                raise RuntimeError(f"{self.name}: Could not get init status. Are pumps connected?")
            if not initialized:
                print(f"{self.name}: Initializing pump {pump}...")
                tri.initialize_pump(self.serial, pump=pump)

        for pump in ("A", "B"):
            tri.check_until_initialized(self.serial, pump=pump)
        print(f"{self.name}: Both pumps initialized successfully.")

    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Dispense a volume at a given flow rate (µL/min) on both pumps.

        Calculates run time, starts continuous flow, waits, then stops.
        """
        if not self._connected:
            raise RuntimeError(f"{self.name}: Not connected")
        if flow_rate_ul_min <= 0:
            raise ValueError(f"Flow rate must be > 0, got {flow_rate_ul_min}")
        if volume_ul <= 0:
            raise ValueError(f"Volume must be > 0, got {volume_ul}")

        self.flow_rate_ul_min = abs(flow_rate_ul_min)
        self.flow_rate_ul_sec = self.flow_rate_ul_min / 60.0
        self.counts_per_uL = self.CALIBRATION_VALUES.get(self.flow_rate_ul_min, self.DEFAULT_COUNTS_PER_UL)

        pump_time_sec, total_wait_time = self._calculate_pump_time(volume_ul, self.flow_rate_ul_min)
        print(f"{self.name}: Dispensing {volume_ul} µL at {flow_rate_ul_min} µL/min")
        print(f"{self.name}: Pump time: {pump_time_sec:.2f}s (total wait: {total_wait_time:.2f}s)")

        # Clear buffer, stop, then start fresh
        if self.serial.in_waiting:
            self.serial.read(self.serial.in_waiting)
        self.stop()
        self.serial.flush()
        time.sleep(2)

        # Build and send continuous flow commands
        speed = self._convert_flow_rate(flow_rate_ul_min)
        tri.run_continuous_flow(self.serial, pump="A", command=tri.compose_command_continuous_flow_A(dispense_speed=speed))
        tri.run_continuous_flow(self.serial, pump="B", command=tri.compose_command_continuous_flow_B(dispense_speed=speed))

        # Wait until both valves are in output position
        time.sleep(1)
        while not (tri.is_valve_output(self.serial, "A") and tri.is_valve_output(self.serial, "B")):
            print(f"{self.name}: Waiting for pumps to start dispensing...")
            time.sleep(0.5)

        # Run for calculated duration
        start = time.time()
        while time.time() - start < pump_time_sec:
            print(f"{self.name}: Pumping... {time.time() - start:.2f}/{pump_time_sec:.2f}s")
            time.sleep(60)

        self.stop()
        print(f"{self.name}: Dispense complete — {volume_ul} µL dispensed")

    def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Not implemented for this pump model."""
        print(f"{self.name}: Aspirate not implemented for this pump model.")

    def set_flow_rate(self, flow_rate_ul_min: float) -> None:
        """Send a raw output_speed command to the device."""
        if not self._connected:
            raise RuntimeError(f"{self.name}: Not connected")
        self.serial.write(f"output_speed {self._convert_flow_rate(flow_rate_ul_min)}\r\n".encode())

    def stop(self) -> None:
        """Stop both pumps."""
        if not self._connected or not self.serial or not self.serial.is_open:
            return
        for pump in ("A", "B"):
            try:
                tri.stop_pump(self.serial, pump=pump)
                print(f"{self.name}: Stopped pump {pump}")
                time.sleep(0.5)
            except Exception as e:
                print(f"{self.name}: Error stopping pump {pump}: {e}")

    def status(self) -> str:
        """Return a status string for both pumps."""
        if not self._connected:
            return f"{self.name}: Not connected"
        try:
            a = tri.check_status(self.serial, pump="A")
            b = tri.check_status(self.serial, pump="B")
            return f"{self.name}: Pump A: {a}, Pump B: {b}"
        except Exception as e:
            return f"{self.name}: Error getting status — {e}"

    def close(self) -> None:
        """Stop pumps and close serial connection."""
        if self.serial and self.serial.is_open:
            try:
                self.stop()
            except Exception:
                pass
            self.serial.close()
            self._connected = False
            print(f"{self.name}: Closed")

    # --- Private helpers ---

    def _convert_flow_rate(self, ul_min: float) -> int:
        """Convert µL/min to device speed in counts/second."""
        counts_per_uL = self.CALIBRATION_VALUES.get(abs(ul_min), self.DEFAULT_COUNTS_PER_UL)
        return int((abs(ul_min) / 60.0) * counts_per_uL)

    def _convert_volume_to_counts(self, volume_ul: float) -> int:
        """Convert µL to device counts."""
        return int(abs(volume_ul) * self.counts_per_uL)

    def _calculate_pump_time(self, volume_ul: float, flow_rate_ul_min: float,
                              buffer_sec: float = 2.0) -> tuple:
        """Return (pump_time_sec, pump_time_sec + buffer_sec) for a given volume and rate."""
        if flow_rate_ul_min <= 0 or volume_ul <= 0:
            raise ValueError("Volume and flow rate must be > 0")
        pump_time = abs(volume_ul) / (abs(flow_rate_ul_min) / 60.0)
        return pump_time, pump_time + buffer_sec

    def get_pump_parameters(self) -> None:
        """Print current pump configuration."""
        print(f"Pump parameters for {self.name}:")
        print(f"  Flow rate:      {self.flow_rate_ul_min} µL/min ({self.flow_rate_ul_sec:.4f} µL/sec)")
        print(f"  µL per count:   {self.uL_per_count}")
        print(f"  Counts per µL:  {self.counts_per_uL:.4f}")
        print(f"  Connected:      {self._connected}")
        print(f"  Port:           {self.port} @ {self.baudrate} baud")