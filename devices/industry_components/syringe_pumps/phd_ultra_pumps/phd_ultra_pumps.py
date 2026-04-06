# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

import serial, time
from typing import Optional

from ..syringe_pumps import SyringePump  # import the abstract base class from parent package


class PhdUltraPump(SyringePump):
    """Minimal driver for a Harvard-Apparatus PHD-Ultra syringe pump (µL units).

    Now implements the SyringePump ABC used by AUTO_ZAHRT.

    Units:
        - flow_rate: µL/min
        - volume:    µL
    """

    # Air-Tite syringe catalogue                   (total-volume mL : I.D. mm)
    AIR_TITE_SYRINGES = {1: 4.69, 2.5: 9.65, 5: 12.45, 10: 15.90, 20: 20.05, 24: 22.90}

    def __init__(
        self,
        port: str = "COM19",
        baudrate: int = 9600,
        timeout: float = 1.0,
        address: int = 0,
        pause: float = 0.10,
        name: str = "PhdUltraPump",
    ):
        # Keep original behavior: open serial port immediately
        self.name = name
        self.address, self.pause = address, pause
        self.ser = serial.Serial(
            port,
            baudrate,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=timeout,
            rtscts=False,
            dsrdtr=False,
            xonxoff=False,
        )
        self.syringe_size_ml: Optional[float] = None  # record current syringe

        # NEW: for SyringePump lifecycle
        self._connected: bool = False
        self._default_flow_ul_min: Optional[float] = None
        self._last_status_msg: str = "Not connected"

    # ---------- SyringePump ABC: lifecycle ----------

    def connect(self) -> None:
        """Connect to the syringe pump device."""
        if not self.ser.is_open:
            self.ser.open()
        # We don't force any mode here; caller can use quick_start_infuse() etc.
        self._connected = True
        self._last_status_msg = "Connected"

    def _ensure_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("PhdUltraPump is not connected. Call connect() first.")

    # ---------- low-level ----------
    def _build(self, body: str) -> bytes:
        prefix = f"{self.address}" if self.address else ""
        return f"{prefix}{body}\r".encode()

    def send(self, body: str) -> str:
        self.ser.reset_input_buffer()
        self.ser.write(self._build(body))
        time.sleep(self.pause)
        reply = self.ser.read_all().decode(errors="ignore").strip()
        return reply

    # ---------- setup / mode ----------
    def quick_start_infuse(self) -> str:
        mode = self.send("mode").lower()
        if ("infuse only" in mode) or ("qs i" in mode):
            return mode                    # already correct
        if "satellite" in mode:
            self.send("unlock")
            time.sleep(self.pause)
        return self.send("load qs i")

    # ---------- syringe convenience ----------
    def select_syringe(self, volume_ml: float) -> None:
        """
        Select the syringe size (mL), as required by SyringePump.

        Configures the pump for one of the predefined Air-Tite syringes.
        """
        self._ensure_connected()

        diameter = self.AIR_TITE_SYRINGES.get(volume_ml)
        if diameter is None:
            raise ValueError(
                f"Unsupported syringe size {volume_ml} mL. "
                f"Choose from {list(self.AIR_TITE_SYRINGES.keys())}"
            )
        self.syringe_size_ml = volume_ml
        # Informational volume setting on the pump
        self.set_syringe_volume(volume_ml * 1000, "ul")
        self.set_diameter(diameter)
        self._last_status_msg = f"Syringe selected: {volume_ml} mL (diameter={diameter:.3f} mm)"

    def set_diameter(self, mm: float) -> str:
        return self.send(f"diameter {mm:.3f}")

    def set_syringe_volume(self, vol_ul: float, unit: str = "ul") -> str:
        return self.send(f"svolume {vol_ul} {unit}")

    # ---------- run control ----------
    def set_rate(self, rate_ul_min: float, unit: str = "ul/min") -> str:
        return self.send(f"irate {rate_ul_min:.4g} {unit}")

    def clear_volume_counter(self) -> str:
        return self.send("cvolume")

    def set_target_volume(self, vol_ul: float, unit: str = "ul") -> str:
        return self.send(f"tvolume {vol_ul} {unit}")

    def run(self) -> str:
        return self.send("irun")

    def infuse_volume(self, vol_ul: float, rate_ul_min: float) -> None:
        """
        Infuse *vol_ul* at *rate_ul_min* and let the pump stop automatically.

        Blocking: waits for the estimated duration plus a small padding.
        """
        self._ensure_connected()

        if rate_ul_min <= 0:
            raise ValueError("rate_ul_min must be > 0.")
        if vol_ul <= 0:
            raise ValueError("vol_ul must be > 0.")

        self.set_rate(rate_ul_min, "ul/min")
        self.clear_volume_counter()
        self.set_target_volume(vol_ul, "ul")
        self.run()  # pump stops when target reached

        duration_sec = vol_ul / rate_ul_min * 60.0  # (µL) ÷ (µL/min) × 60 s/min
        duration_sec = duration_sec + 2.0           # padding
        time.sleep(duration_sec)

        self._last_status_msg = (
            f"Infused {vol_ul:.1f} µL at {rate_ul_min:.2f} µL/min "
            f"(~{duration_sec:.1f} s run)"
        )

    def withdraw(self) -> str:
        if "withdraw" not in self.send("mode").lower():
            raise RuntimeError("Current mode does not allow withdraw")
        return self.send("wrun")

    # ---------- SyringePump ABC: high-level ops ----------

    def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """
        Aspirate `volume_ul` (µL) at `flow_rate_ul_min` (µL/min).

        NOTE:
        For now this uses the same direction as `infuse_volume`, because only
        infuse commands are present in the original driver snippet. If you
        configure the pump so that "infuse" corresponds to aspiration in
        your plumbing, this will behave as expected.
        """
        self.infuse_volume(volume_ul, flow_rate_ul_min)

    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """
        Dispense `volume_ul` (µL) at `flow_rate_ul_min` (µL/min).

        Currently implemented identically to `aspirate`, relying on your
        physical setup (tubing orientation) to determine which direction
        corresponds to which logical operation.
        """
        self.infuse_volume(volume_ul, flow_rate_ul_min)

    def set_flow_rate(self, flow_rate_ul_min: float) -> None:
        """Set a default flow rate (µL/min) for subsequent operations."""
        self._ensure_connected()

        if flow_rate_ul_min <= 0:
            raise ValueError("flow_rate_ul_min must be > 0.")
        self.set_rate(flow_rate_ul_min, "ul/min")
        self._default_flow_ul_min = flow_rate_ul_min
        self._last_status_msg = f"Default flow set to {flow_rate_ul_min:.2f} µL/min"

    def stop(self) -> None:
        """Stop any ongoing aspiration/dispense operation promptly."""
        if not self._connected:
            return
        self.send("stop")
        self._last_status_msg = "Stopped"

    # ---------- diagnostics ----------
    def get_status(self) -> str:
        return self.send("status")

    def get_version(self) -> str:
        return self.send("ver")
    
    def get_current_flow_rate_ul_min(self) -> Optional[float]:
        """
        Query the pump for its current flow rate (µL/min).

        Uses the CRATE pump-chain command:
            - 'crate' → "Infusing at # xl/xxx" or "Withdrawing at # xl/xxx"
        We assume rates are configured in µL/min (ul/min) via set_rate().
        Returns:
            +flow (µL/min) for infuse
            -flow (µL/min) for withdraw
            None if pump is not moving or response is not parseable.
        """
        self._ensure_connected()

        reply = self.send("crate")  # CRATE: current rate command

        if not reply:
            return None

        # Take the first non-empty line
        lines = [ln.strip() for ln in reply.splitlines() if ln.strip()]
        if not lines:
            return None

        line = lines[0]

        # Strip optional address prefix: "##:..."
        if ":" in line:
            _, line = line.split(":", 1)
            line = line.strip()

        direction = None
        if line.lower().startswith("infusing at"):
            direction = +1
            payload = line[len("Infusing at"):].strip()
        elif line.lower().startswith("withdrawing at"):
            direction = -1
            payload = line[len("Withdrawing at"):].strip()
        else:
            # Not in the documented format → treat as unknown / idle
            return None

        # payload should look like "3000 ul/min" or "0.05 ml/min"
        parts = payload.split()
        if len(parts) < 2:
            return None

        try:
            rate_value = float(parts[0])
        except ValueError:
            return None

        unit = parts[1].lower()

        # Convert to µL/min
        if unit in ("ul/min", "µl/min"):
            rate_ul_min = rate_value
        elif unit in ("ml/min",):
            rate_ul_min = rate_value * 1000.0
        elif unit in ("nl/min",):
            rate_ul_min = rate_value / 1000.0
        else:
            # Unknown unit → don’t guess
            return None

        return direction * rate_ul_min


    def status(self) -> str:  # SyringePump ABC
        """Return a string representing the current status of the pump."""
        if not self._connected:
            return "Not connected"

        try:
            raw_status = self.get_status().strip()
        except Exception as exc:
            raw_status = f"status read error: {exc!r}"

        # Try to get current flow rate
        try:
            flow = self.get_current_flow_rate_ul_min()
            if flow is None:
                flow_str = "idle (no flow / no CRATE data)"
            else:
                direction = "infuse" if flow > 0 else "withdraw"
                flow_str = f"{abs(flow):.3f} µL/min ({direction})"
        except Exception as exc:
            flow_str = f"unknown (CRATE error: {exc!r})"

        return flow

    # ---------- housekeeping ----------
    def close(self) -> None:
        """Shutdown the pump: stop and close serial port."""
        try:
            if self._connected:
                self.stop()
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
            self._connected = False
            self._last_status_msg = "Closed"

    def safe_shutdown(self, success: bool) -> None:
        pass


# ----------------------------------------------------------------------
# Self-test harness (executes if you `python phd_ultra.py`)
# ----------------------------------------------------------------------
PORT, BAUD, PAUSE = "COM18", 9600, 0.25

def _run_selftest():
    pump = None
    try:
        pump = PhdUltraPump(port=PORT, baudrate=BAUD)
        pump.connect()   # <-- NEW: use the SyringePump lifecycle

        tests = [
            ("mode",               lambda: pump.send("mode")),
            ("quick_start_infuse", pump.quick_start_infuse),
            ("select_syringe 10 mL", lambda: pump.select_syringe(10)),
            ("set_rate 3000 µL/min",  lambda: pump.set_rate(3000)),
            ("infuse 3000 µL", lambda: pump.infuse_volume(3000, 3000)),
            ("get_version",        pump.get_version),
        ]

        print(f"\n===== PHD-Ultra self-test on {PORT} @ {BAUD} baud =====")
        for name, fn in tests:
            try:
                reply = fn()
                print(f"[PASS] {name:30s} → {repr(reply)}")
            except Exception as exc:
                print(f"[FAIL] {name:30s} → {exc}")
            time.sleep(PAUSE)
    finally:
        if pump:
            pump.close()
        print("===== Test complete — port closed =====")

if __name__ == "__main__":
    _run_selftest()
