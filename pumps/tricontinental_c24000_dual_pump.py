from __future__ import annotations

import time
import serial
from typing import Optional

from pumps.pumps import Pump


class TriContinentC24000MPDual(Pump):
    """
    Dual-piston (2x C24000/C24000MP) driver via:
      PC (Python) -> USB serial -> Arduino gateway -> RS-485 -> pumps

    Units:
      flow_rate_ul_min: µL/min
      volume_ul: µL
    """

    def __init__(
        self,
        port: str,
        baud_rate: int = 115200,
        timeout_s: float = 2.0,
        syringe_ul: float = 12500.0,
        default_nmode: int = 2,
        startup_home: bool = True,
    ):
        self.port = port
        self.baud_rate = baud_rate
        self.timeout_s = timeout_s

        self.syringe_ul = float(syringe_ul)
        self.default_nmode = int(default_nmode)
        if self.default_nmode not in (0, 1, 2):
            raise ValueError("default_nmode must be 0, 1, or 2")

        self.startup_home = bool(startup_home)

        self._connected = False
        self._ser: Optional[serial.Serial] = None
        self._default_flow_ul_min: float = 100.0

    # ------------------- low-level Arduino protocol -------------------
    def _write_line(self, line: str) -> None:
        assert self._ser is not None
        self._ser.write((line.strip() + "\n").encode("utf-8"))

    def _read_line(self) -> str:
        assert self._ser is not None
        raw = self._ser.readline().decode("utf-8", errors="replace").strip()
        return raw

    def _cmd(self, line: str, expect_ok: bool = True, timeout_s: Optional[float] = None) -> str:
        """
        Send one command line, return the single-line reply.
        """
        if not self._ser or not self._ser.is_open:
            raise RuntimeError("Arduino serial is not open")

        if timeout_s is None:
            timeout_s = self.timeout_s

        # Flush stale input
        self._ser.reset_input_buffer()
        self._write_line(line)

        t0 = time.time()
        while time.time() - t0 < timeout_s:
            resp = self._read_line()
            if not resp:
                continue
            if resp.startswith("OK"):
                if expect_ok:
                    return resp
                return resp
            if resp.startswith("ERR"):
                raise RuntimeError(f"Arduino error for '{line}': {resp}")
            # Allow asynchronous chatter if you ever add it later
        raise TimeoutError(f"Timeout waiting for reply to '{line}'")

    # ------------------- required Pump interface -------------------
    def connect(self) -> None:
        self._ser = serial.Serial(self.port, self.baud_rate, timeout=self.timeout_s)
        # sanity check
        self._cmd("PING")

        # configure syringe volume and default mode
        self._cmd(f"CONFIG SYRINGE_UL {self.syringe_ul}")
        self._cmd(f"CONFIG NMODE {self.default_nmode}")

        if self.startup_home:
            # home both pumps (Arduino firmware homes in N0 internally for INIT)
            self._cmd("PUMP 1 INIT", timeout_s=10.0)
            self._cmd("PUMP 2 INIT", timeout_s=10.0)

        self._connected = True

    def set_flow_rate(self, flow_rate_ul_min: float) -> None:
        self._default_flow_ul_min = float(flow_rate_ul_min)

    def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        self._ensure_connected()
        flow = float(flow_rate_ul_min)
        vol = float(volume_ul)
        if flow <= 0 or vol <= 0:
            raise ValueError("flow_rate_ul_min and volume_ul must be > 0")

        # Blocking dual-piston aspiration of the *system line*
        # (usually you’ll use DISPENSE for pushing downstream; but supported)
        # Arduino returns OK dual_running then OK dual_done.
        self._cmd(f"DUAL START ASPIRATE {flow} {vol}", expect_ok=True, timeout_s=2.0)
        self._wait_for_dual_done()

    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        self._ensure_connected()
        flow = float(flow_rate_ul_min)
        vol = float(volume_ul)
        if flow <= 0 or vol <= 0:
            raise ValueError("flow_rate_ul_min and volume_ul must be > 0")

        self._cmd(f"DUAL START DISPENSE {flow} {vol}", expect_ok=True, timeout_s=2.0)
        self._wait_for_dual_done()

    def stop(self) -> None:
        if not self._ser or not self._ser.is_open:
            return
        # cooperative stop
        self._cmd("DUAL STOP", timeout_s=2.0)

    def status(self) -> str:
        self._ensure_connected()
        return self._cmd("STATUS", timeout_s=2.0)

    def close(self) -> None:
        if self._ser:
            try:
                self.stop()
            except Exception:
                pass
            try:
                self._ser.close()
            finally:
                self._ser = None
                self._connected = False

    # ------------------- convenience helpers -------------------
    def dispense_default(self, volume_ul: float) -> None:
        self.dispense(self._default_flow_ul_min, volume_ul)

    def aspirate_default(self, volume_ul: float) -> None:
        self.aspirate(self._default_flow_ul_min, volume_ul)

    def _wait_for_dual_done(self) -> None:
        """
        Wait until Arduino sends 'OK dual_done'.
        """
        assert self._ser is not None
        t0 = time.time()
        # Allow long operations
        timeout_s = 600.0
        while time.time() - t0 < timeout_s:
            resp = self._read_line()
            if not resp:
                continue
            if resp.startswith("OK dual_done"):
                return
            if resp.startswith("ERR"):
                raise RuntimeError(f"Arduino dual error: {resp}")
        raise TimeoutError("Timed out waiting for dual_done")

    def _ensure_connected(self) -> None:
        if not self._connected or not self._ser or not self._ser.is_open:
            raise RuntimeError("Pump not connected. Call connect().")
