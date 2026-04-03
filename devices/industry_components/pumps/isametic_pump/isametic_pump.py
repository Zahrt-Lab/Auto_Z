# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

# ismatic_pump.py

from __future__ import annotations
import time
import serial
from typing import Optional

from ..pumps import Pump   # import the abstract Pump class from parent pumps package


class IsmaticPump(Pump):
    """
    High-level wrapper for the Ismatic ISM834A V2.10 pump implementing the Pump ABC.

    Units (per Pump interface):
        - flow_rate: µL/min
        - volume:    µL

    This class uses simple time-based control: for a given flow rate and volume,
    it computes how long to run the pump, starts it, sleeps, then stops.
    """

    def __init__(
        self,
        port: str = "COM14",
        addr: int = 1,
        ml_per_rev: float = 0.085,  # <-- replace with your calibrated value
        baudrate: int = 9600,
        wake_delay_s: float = 5.0,
        timeout_s: float = 1.0,
        aspirate_cw: bool = True,
        name: str = "IsmaticPump",
    ) -> None:
        """
        Parameters
        ----------
        port : str
            Serial port, e.g., "COM14" (Windows) or "/dev/ttyUSB0" (Linux).
        addr : int
            Pump address on the RS-232 bus (1–8).
        ml_per_rev : float
            Calibrated volume per revolution in mL/rev.
        wake_delay_s : float
            Delay after opening the serial port to allow the pump to wake up.
        timeout_s : float
            Serial read timeout (seconds).
        aspirate_cw : bool
            If True: CW == aspirate, CCW == dispense.
            If False: CCW == aspirate, CW == dispense.
        name : str
            Optional name for the pump instance.
        """
        self.name = name
        self.port = port
        self.addr = addr
        self.ml_per_rev = ml_per_rev
        self.baudrate = baudrate
        self.timeout_s = timeout_s
        self.wake_delay_s = wake_delay_s
        self.aspirate_cw = aspirate_cw

        self._ser: Optional[serial.Serial] = None
        self._connected: bool = False
        self._default_flow_ul_min: Optional[float] = None
        self._last_status_msg: str = "Not connected"

    # ------------------------------------------------------------------
    # Low-level helpers (RS-232 protocol)
    # ------------------------------------------------------------------

    def _open_serial(self) -> None:
        if self._ser is None or not self._ser.is_open:
            self._ser = serial.Serial(
                self.port,
                self.baudrate,
                bytesize=8,
                parity=serial.PARITY_NONE,
                stopbits=1,
                timeout=self.timeout_s,
            )
            time.sleep(self.wake_delay_s)
            # Flush any residual data in the buffer after wake delay
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()

    def _send(self, cmd: str) -> str:
        """Send ASCII command (without CR) and return reply as string."""
        if self._ser is None or not self._ser.is_open:
            raise RuntimeError("Serial port is not open; call connect() first.")
        self._ser.reset_input_buffer()
        self._ser.write((cmd + "\r").encode("ascii"))
        resp = self._ser.read_until(b"\r").decode("ascii", errors="ignore").strip()
        # optional LF may follow
        self._ser.read(1)
        return resp

    def _set_direction_cw(self) -> str:
        return self._send(f"{self.addr}J")  # clockwise

    def _set_direction_ccw(self) -> str:
        return self._send(f"{self.addr}K")  # counter-clockwise

    def _start(self) -> str:
        return self._send(f"{self.addr}H")

    def _stop(self) -> str:
        return self._send(f"{self.addr}I")

    def _set_rpm(self, rpm: float) -> str:
        """
        Set motor speed in rpm (device accepts hundredths of rpm).
        Returns '*' on success.
        """
        v = int(round(rpm * 100))  # 0.01 rpm steps
        return self._send(f"{self.addr}S{v:06d}")

    def _get_rpm(self) -> float:
        """Query current rpm as float."""
        resp = self._send(f"{self.addr}S")
        try:
            return float(resp)
        except ValueError:
            # In case of weird response, treat as stopped
            return 0.0

    def _set_flow_ml_min(self, flow_ml_min: float) -> float:
        """
        Set flow in mL/min by converting to rpm.
        Returns the *achieved* flow (mL/min) after quantization.
        """
        if self.ml_per_rev <= 0:
            raise ValueError("ml_per_rev must be > 0. Calibrate before use.")
        rpm = round(flow_ml_min / self.ml_per_rev, 2)  # quantize to 0.01 rpm
        ack = self._set_rpm(rpm)
        if ack != "*":
            raise RuntimeError(f"Pump did not acknowledge speed command: {ack!r}")
        achieved_ml_min = rpm * self.ml_per_rev
        return achieved_ml_min

    def _get_flow_ml_min(self) -> float:
        """Compute current mL/min from rpm and ml_per_rev."""
        rpm = self._get_rpm()
        return rpm * self.ml_per_rev

    # ------------------------------------------------------------------
    # Pump ABC implementation (high-level operations)
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Connect to the pump device."""
        self._open_serial()
        # Query current RPM to verify pump is responsive
        try:
            _ = self._get_rpm()
        except Exception as e:
            print(f"Warning: Initial pump query failed: {e}")
        # Set default direction
        self._set_direction_cw()
        self._connected = True
        self._last_status_msg = "Connected"

    def _ensure_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("Pump is not connected. Call connect() first.")

    def _flow_ul_min_to_ml_min(self, flow_rate_ul_min: float) -> float:
        return flow_rate_ul_min / 1000.0

    def _run_for_volume(
        self,
        flow_rate_ul_min: float,
        volume_ul: float,
        direction: str,
    ) -> None:
        """
        Internal helper that:
        - sets direction
        - sets flow rate
        - runs for the required time to move `volume_ul` at `flow_rate_ul_min`
        - stops
        This call is blocking.
        """
        self._ensure_connected()

        if flow_rate_ul_min <= 0:
            raise ValueError("flow_rate_ul_min must be > 0.")
        if volume_ul <= 0:
            raise ValueError("volume_ul must be > 0.")

        # Set direction
        if direction == "cw":
            self._set_direction_cw()
        elif direction == "ccw":
            self._set_direction_ccw()
        else:
            raise ValueError("direction must be 'cw' or 'ccw'.")

        # Convert flow to ml/min and set on device
        flow_ml_min = self._flow_ul_min_to_ml_min(flow_rate_ul_min)
        achieved_ml_min = self._set_flow_ml_min(flow_ml_min)

        # Compute run time based on achieved (quantized) flow
        achieved_ul_min = achieved_ml_min * 1000.0  # back to µL/min
        if achieved_ul_min <= 0:
            raise RuntimeError("Achieved flow rate is zero; check calibration.")

        run_time_min = volume_ul / achieved_ul_min
        run_time_s = run_time_min * 60.0

        # Run pump
        self._start()
        time.sleep(run_time_s)
        self._stop()

        self._last_status_msg = (
            f"Completed move: {volume_ul:.1f} µL at ~{achieved_ul_min:.2f} µL/min "
            f"over {run_time_s:.2f} s ({direction.upper()})"
        )

    def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Aspirate `volume_ul` (µL) at `flow_rate_ul_min` (µL/min)."""
        direction = "cw" if self.aspirate_cw else "ccw"
        self._run_for_volume(flow_rate_ul_min, volume_ul, direction)

    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Dispense `volume_ul` (µL) at `flow_rate_ul_min` (µL/min)."""
        # Opposite of aspirate
        direction = "ccw" if self.aspirate_cw else "cw"
        self._run_for_volume(flow_rate_ul_min, volume_ul, direction)

    def set_flow_rate(self, flow_rate_ul_min: float) -> None:
        """Set a default flow rate (µL/min) for subsequent operations."""
        self._ensure_connected()
        if flow_rate_ul_min <= 0:
            raise ValueError("flow_rate_ul_min must be > 0.")
        flow_ml_min = self._flow_ul_min_to_ml_min(flow_rate_ul_min)
        achieved_ml_min = self._set_flow_ml_min(flow_ml_min)
        self._default_flow_ul_min = achieved_ml_min * 1000.0
        self._last_status_msg = (
            f"Default flow set to ~{self._default_flow_ul_min:.2f} µL/min"
        )

    def stop(self) -> None:
        """Stop any ongoing aspiration/dispense operation promptly."""
        if not self._connected:
            return
        self._stop()
        self._last_status_msg = "Stopped"

    def status(self) -> str:  # type: ignore[override]
        """Return a string representing the current status of the pump."""
        if not self._connected:
            return "Not connected"

        try:
            rpm = self._get_rpm()
            flow_ml_min = rpm * self.ml_per_rev
            flow_ul_min = flow_ml_min * 1000.0
            state = "Running" if rpm > 0 else "Stopped"
            return flow_ul_min
        except Exception as exc:
            return f"Connected, status read error: {exc!r}. Last message: {self._last_status_msg}"

    def close(self) -> None:
        """Shutdown the pump: stop it and close the serial port."""
        try:
            self.stop()
        finally:
            if self._ser is not None and self._ser.is_open:
                self._ser.close()
            self._connected = False
            self._last_status_msg = "Closed"


# ----------------------------------------------------------------------
# Example standalone usage
# ----------------------------------------------------------------------
if __name__ == "__main__":
    pump = IsmaticPump(
        port="COM14",
        addr=1,
        ml_per_rev=0.085,   # <-- put your calibrated value here
        aspirate_cw=True,   # <-- set depending on your tubing orientation
    )

    try:
        pump.connect()
        print(pump.status())

        # Example: aspirate 500 µL at 50 µL/min
        pump.aspirate(flow_rate_ul_min=50.0, volume_ul=500.0)
        print(pump.status())

        # Example: dispense 500 µL at 50 µL/min
        pump.dispense(flow_rate_ul_min=50.0, volume_ul=500.0)
        print(pump.status())

    finally:
        pump.close()
        print("Pump closed.")
