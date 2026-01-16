import serial
import time

class DH2000LightSource:
    """
    Wraps the Arduino DH-2000 TTL controller.

    Arduino commands:
      o/c/d/h -> prints OK
      s       -> prints 3 lines, no OK
    """
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 2.0,
                 retries: int = 10, boot_delay_s: float = 2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.retries = retries
        self.boot_delay_s = boot_delay_s
        self.name = "DH2000"

        self.ser = None

    # --- lifecycle ---
    def connect(self):
        self.ser = serial.Serial(self.port, baudrate=self.baudrate, timeout=self.timeout)
        time.sleep(self.boot_delay_s)
        self._drain()

    def close(self):
        try:
            if self.ser:
                self.ser.close()
        finally:
            self.ser = None

    # --- internal IO ---
    def _drain(self, seconds: float = 0.75) -> None:
        end = time.time() + seconds
        while time.time() < end:
            while self.ser and self.ser.in_waiting:
                try:
                    self.ser.readline()
                except Exception:
                    break
            time.sleep(0.01)

    def _readline_str(self) -> str:
        raw = self.ser.readline() if self.ser else b""
        if not raw:
            return ""
        return raw.decode("utf-8", errors="ignore").strip()

    def dh2000_command(self, command: str, expect_ok: bool = True) -> None:
        if not self.ser:
            raise RuntimeError("DH2000 serial not connected")
        if not isinstance(command, str) or len(command) != 1:
            raise ValueError("Command must be a single character")
        if command not in ['o', 'c', 'h', 'd', 's']:
            raise ValueError("Invalid command character")
        
        self.ser.write((command + "\n").encode("ascii", errors="ignore"))
        self.ser.flush()

        if not expect_ok:
            return

        deadline = time.time() + (self.timeout or 2.0)
        while time.time() < deadline:
            line = self._readline_str()
            if line == "OK":
                return
        raise RuntimeError(f"Timed out waiting for OK after '{c}'")

    # --- public control ---
    def shutter_open(self):   self.dh2000_command("o", expect_ok=True)
    def shutter_close(self):  self.dh2000_command("c", expect_ok=True)
    def halogen_toggle(self): self.dh2000_command("h", expect_ok=True)
    def deuterium_toggle(self): self.dh2000_command("d", expect_ok=True)

    def status(self) -> dict:
        """
        Returns dict:
          {'shutter_open': bool|None, 'halogen_on': bool|None, 'deuterium_on': bool|None, 'raw': [lines]}
        """
        self.dh2000_command("s", expect_ok=False)
        dh2000_components_status = []
        timeout = time.time() + (self.timeout or 2.0)
        while time.time() < timeout and len(dh2000_components_status) < 3:
            dh2000_component_status = self._readline_str()
            if dh2000_component_status:
                dh2000_components_status.append(dh2000_component_status)

        def _parse_bool(dh2000_component_status: str, key: str):
            if key.lower() in dh2000_component_status.lower():
                if "OPEN" in dh2000_component_status.upper() or "ON" in dh2000_component_status.upper():
                    return True
                if "CLOSED" in dh2000_component_status.upper() or "OFF" in dh2000_component_status.upper():
                    return False
            return None

        shutter = None
        hal = None
        deut = None
        for dh2000_component_status in dh2000_components_status:
            if shutter is None:
                shutter = _parse_bool(dh2000_component_status, "Shutter")
            if hal is None:
                hal = _parse_bool(dh2000_component_status, "Halogen")
            if deut is None:
                deut = _parse_bool(dh2000_component_status, "Deuterium")

        return {"shutter_open": shutter, "halogen_on": hal, "deuterium_on": deut, "arduino_output": dh2000_components_status}

    # --- safety policies you requested ---
    def ensure_success_state(self):
        """
        Success end-state: Halogen ON + Deuterium ON + Shutter OPEN.
        Uses status lines to avoid wrong-direction toggles.
        Retries up to self.retries.
        """
        last_error = None
        for _ in range(self.retries):
            try:
                status = self.status()
                # If parsing failed, it will try again for self.retries times
                if status["halogen_on"] is None or status["deuterium_on"] is None or status["shutter_open"] is None:
                    raise RuntimeError(f"Unparseable status: {status    ['arduino_output']}")

                if not status["halogen_on"]:
                    self.halogen_toggle()
                if not status["deuterium_on"]:
                    self.deuterium_toggle()
                if not status["shutter_open"]:
                    self.shutter_open()

                # verify
                st2 = self.status()
                if st2["halogen_on"] and st2["deuterium_on"] and st2["shutter_open"]:
                    return
                raise RuntimeError(f"Did not reach success state. status={st2}")
            except Exception as e:
                last_err = e
                time.sleep(0.25)
        raise RuntimeError(f"ensure_success_state failed after {self.retries} attempts: {last_err}")

    def safe_shutdown(self):
        """
        Failure policy: close shutter + both lamps OFF.
        Uses status lines to avoid wrong-direction toggles.
        Retries up to self.retries, but caller should catch errors and continue shutdown.
        """
        last_error = None
        for _ in range(self.retries):
            try:
                status = self.status()
                if status["halogen_on"] is None or status["deuterium_on"] is None or status["shutter_open"] is None:
                    raise RuntimeError(f"Unparseable status: {status['arduino_output']}")

                # close shutter first (your spec)
                if status["shutter_open"]:
                    self.shutter_close()

                # then lamps OFF
                status2 = self.status()
                if status2["halogen_on"]:
                    self.halogen_toggle()
                if status2["deuterium_on"]:
                    self.deuterium_toggle()

                # verify
                status3 = self.status()
                if (status3["shutter_open"] is False) and (status3["halogen_on"] is False) and (status3["deuterium_on"] is False):
                    return
                raise RuntimeError(f"Did not reach OFF state. status={status3}")
            except Exception as e:
                last_error = e
                time.sleep(0.25)
        raise RuntimeError(f"safe_shutdown failed after {self.retries} attempts: {last_error}")