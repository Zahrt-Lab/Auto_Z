# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Andrew Zahrt
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

import ctypes
import re
from typing import Optional, Tuple, Union

from ..liquid_handlers import LiquidHandler

# ---------- low-level helpers (return BYTES; callers decode/parse) ----------

def immediate(unitid: int, command: str) -> bytes:
    try:
        lib = ctypes.windll.gsioc32
        icmd = lib.ICmd
        rsp = ctypes.create_string_buffer(256)
        rsplen = ctypes.c_int(256)
        icmd(unitid, command.encode("utf-8"), rsp, rsplen)
        return rsp.value
    except OSError as ex:
        print("WARNING:", ex)
        return b"Error"

def buffered(unitid: int, command: str) -> bytes:
    try:
        lib = ctypes.windll.gsioc32
        bcmd = lib.BCmd
        rsp = ctypes.create_string_buffer(256)
        rsplen = ctypes.c_int(256)
        bcmd(unitid, command.encode("utf-8"), rsp, rsplen)
        return rsp.value
    except OSError as ex:
        print("WARNING:", ex)
        return b"Error"

def _decode(b: bytes) -> str:
    return b.decode("ascii", "ignore").strip("\x00\r\n ")

# ---------- parsing helpers ----------

_XY_RE = re.compile(r"X[:=\s]*([-\d.]+)\s*[,; ]\s*Y[:=\s]*([-\d.]+)", re.I)
_XY_SLASH_RE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*/\s*([+-]?\d+(?:\.\d+)?)\s*$")
_Z_RE  = re.compile(r"Z[:=\s]*([-\d.]+)", re.I)

def _parse_xy(s: str) -> Tuple[float, float]:
    s = s.strip()
    # Preferred: "123.45/67.89" or "-1/-1"
    m = _XY_SLASH_RE.match(s)
    if m:
        return float(m.group(1)), float(m.group(2))
    # Also accept "X=.., Y=.." / "X .. Y .."
    m = _XY_RE.search(s) or re.search(r"X\s*([-\d.]+)\s+Y\s*([-\d.]+)", s, re.I)
    if m:
        return float(m.group(1)), float(m.group(2))
    # Last resort: first two numbers in the string
    nums = re.findall(r"[+-]?\d+(?:\.\d+)?", s)
    if len(nums) >= 2:
        return float(nums[0]), float(nums[1])
    raise ValueError("Could not parse XY from: %r" % s)

def _parse_z(s: str) -> float:
    m = _Z_RE.search(s)
    if not m:
        m = re.search(r"\b([-\d.]+)\b", s)
    if not m:
        raise ValueError("Could not parse Z from: %r" % s)
    return float(m.group(1))

# ---------- device class ----------

class GX281(LiquidHandler):
    DEVICE_TYPE = 'GX281'

    def __init__(self, name: str, uid: int = 25):
        super().__init__(name)
        self.uid = uid
        self.XMIN, self.XMAX = 0, 700
        self.YMIN, self.YMAX = 0, 380
        self.ZMIN, self.ZMAX = 0, 125
        self.SAFE_Z = 125

        # Default racks
        self.rack1 = 204
        self.rack2 = 204
        self.rack3 = 204
        self.rack4 = 204
        self.rack5 = 204
        self.rack6 = 204

        self._lib_ok = None  # type: Optional[bool]

    # ---- lifecycle ----
    def connect(self) -> None:
        if self._connected:
            return
        try:
            _ = ctypes.windll.gsioc32
            self._lib_ok = True
        except OSError as ex:
            self._lib_ok = False
            raise RuntimeError("gsioc32.dll not available: %s" % ex)

        # handshake: '%' should give some non-empty response
        rsp = _decode(immediate(self.uid, "%"))
        if not rsp or rsp.lower().startswith("error"):
            raise RuntimeError("GX281 (uid %s) not responding to '%%': %r" % (self.uid, rsp))
        self._connected = True

    def close(self) -> None:
        self._connected = False
        print("Disconnected GX281 uid=%s" % self.uid)

    def stop(self) -> None:
        try:
            if self.get_z() != self.SAFE_Z:
                self.move_z(self.SAFE_Z)
        except Exception as e:
            print("Stop: failed to park Z:", e)

    # ---- core movement ----
    def home(self) -> None:
        self._ensure_conn()
        buffered(self.uid, "SH")

    def get_xy(self) -> Tuple[float, float]:
        self._ensure_conn()
        s = _decode(immediate(self.uid, "X"))
        x, y = _parse_xy(s)
        # Treat -1/-1 as "unknown/busy" rather than a parse failure
        if x == -1.0 and y == -1.0:
            raise RuntimeError("GX281: XY unknown (-1/-1) — not homed or still moving.")
        return x, y

    def move_xy(self, x: float, y: float) -> None:
        self._ensure_conn()
        if x < self.XMIN: x = self.XMIN
        if x > self.XMAX: x = self.XMAX
        if y < self.YMIN: y = self.YMIN
        if y > self.YMAX: y = self.YMAX

        current_z = self.get_z()  # type: float
        if current_z < self.SAFE_Z:
            self.move_z(self.SAFE_Z)

        buffered(self.uid, "SX{}/{}".format(int(x), int(y)))

    def get_z(self) -> float:
        self._ensure_conn()
        s = _decode(immediate(self.uid, "Z"))
        return _parse_z(s)

    def move_z(self, z: float) -> None:
        self._ensure_conn()
        if z < self.ZMIN: z = self.ZMIN
        if z > self.ZMAX: z = self.ZMAX
        buffered(self.uid, "SZ{}".format(int(z)))
    
    def get_safe_z_height(self) -> float:
        """Return the safe Z height (mm) for the liquid handler."""
        return self.SAFE_Z

    # ---- misc/status ----
    def status(self) -> dict:
        try:
            x, y = self.get_xy()
            z = self.get_z()
            return {"ok": True, "code": "ok", "msg": "X=%.2f Y=%.2f Z=%.2f" % (x, y, z)}
        except Exception as e:
            return {"ok": False, "code": "no_response", "msg": str(e)}

    # ---- guard ----
    def _ensure_conn(self) -> None:
        if not self._connected:
            raise RuntimeError("GX281 not connected. Call connect() first.")

# ---------------------- usage ----------------------
import time
if __name__ == "__main__":
    gx = GX281(name="gx281", uid=25)
    gx.connect()
    gx.home()
    time.sleep(5)
    gx.move_xy(120, 50)
    time.sleep(5)
    gx.move_z(80)
    time.sleep(5)
    print(gx.status())
    time.sleep(5)
    gx.stop()
    time.sleep(5)
    gx.close()