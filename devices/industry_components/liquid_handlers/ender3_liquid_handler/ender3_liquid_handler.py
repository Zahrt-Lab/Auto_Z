# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

'''
The purpose of this code is to feed into our liquid handler ender 3 class
which we can use as a 3D printer to control the xyz coordinates of our 3D printer
'''

from .ender3 import ender3
from ..liquid_handlers import LiquidHandler
from ..bed_layout import BedLayout

class Ender3LiquidHandler(ender3, LiquidHandler):
    def __init__(self, port="COM26", baud=115200, timeout=2, verbose=False, name="Ender3_LH"):
        # Initialize the ender3 base class (opens serial connection)
        ender3.__init__(self, port=port, baud=baud, timeout=timeout, verbose=verbose)
        
        # Store name for identification
        self.name = name
        
        # Track connection state
        self._connected = bool(getattr(self, "s", None) and self.s.is_open)

        # Define physical limits for Ender3
        self.XMIN, self.XMAX = 0, 235
        self.YMIN, self.YMAX = 0, 235
        self.ZMIN, self.ZMAX = 0, 250
        self.SAFE_Z = 245  # safe travel height
        
        # Bed layout storage
        self.bed_layouts = {}  # bed_number -> BedLayout instance
    
    @property
    def connected(self) -> bool:
        """Return True if connected to the Ender3."""
        return self._connected

    # optional logging wrappers; base flips the flag
    def connect(self) -> None:
        if self.connected:
            return
        try:
            # If parent defines connect(), use it.
            super().connect()
        except AttributeError:
            # Parent opens in __init__; ensure serial is actually open.
            if not (getattr(self, "s", None) and self.s.is_open):
                raise RuntimeError("Underlying driver has no connect(); and serial isn't open.")
        # In either path, we are connected now:
        self._connected = True
        print(f"Connected to Ender3 on {getattr(self, 'port', getattr(getattr(self,'s',None),'port','?'))}")

    def close(self) -> None:
        p = getattr(self, "port", getattr(getattr(self,'s',None),'port','?'))
        try:
            super().close()
        except AttributeError:
            # Fall back to low-level handle if needed
            if getattr(self, "s", None):
                try: self.s.close()
                except Exception: pass
        finally:
            self._connected = False
        print(f"Disconnected from Ender3 on {p}")

    def stop(self) -> None:
        if self.connected:
            try:
                self.move_z(self.SAFE_Z)
                print(f"Stopping Ender3 liquid handler, setting Z to {self.SAFE_Z} mm")
            except Exception:
                pass
        super().stop()  # parent should e-stop/close

    # --- Core movement commands --------------------------------------------------
    def home(self, lift_mm: float = None) -> None:
        self._ensure_conn()
        # Use SAFE_Z if no lift height specified
        if lift_mm is None:
            lift_mm = self.SAFE_Z
        # Home first (guard in case parent lacks home())
        try:
            super().home("XYZ")
        except AttributeError:
            pass
        self.absolute()
        self.move_z(z=lift_mm)
        self.move_xy(x=0, y=0)

    def move_xy(self, x: float, y: float) -> None:
        self._ensure_conn()  # ← FIX: was _ensure_conn(self)
        x = min(max(x, self.XMIN), self.XMAX)
        y = min(max(y, self.YMIN), self.YMAX)

        current_z = self.get_z()
        if current_z < self.SAFE_Z:             # ← FIX: use <, not !=
            self.move_z(self.SAFE_Z)

        print(f"Moving to X: {x}, Y: {y}")
        self.move(x=x, y=y, z=None, feed=9000)  # no need to return



    
    def get_xy(self) -> tuple[float, float]:
        """Return (X, Y) current coordinates in mm."""
        self._ensure_conn()
        loc = self.location()
        return loc["X"], loc["Y"]

    def move_z(self, z: float) -> None:
        self._ensure_conn()
        if z < self.ZMIN: z = self.ZMIN
        if z > self.ZMAX: z = self.ZMAX
        return self.move(x=None, y=None, z=z, feed=5000)

    def get_z(self) -> float:
        """Return current Z coordinate in mm."""
        self._ensure_conn()
        return self.location()["Z"]
    
    def get_safe_z_height(self) -> float:
        """Return the safe Z height (mm) for the liquid handler."""
        return self.SAFE_Z
    
    def set_bedlayout(self, bed: int, rack_layout: int) -> None:
        """
        Set up a bed layout for a specific bed position.
        
        Args:
            bed: Bed number (position identifier)
            rack_layout: Layout type (e.g., 301 for 20-vial rack)
        """
        self._ensure_conn()
        print(f"Setting bed {bed} to layout {rack_layout}")
        self.bed_layouts[bed] = BedLayout(bed, rack_layout)
    
    def move_to_well(self, bed: int, well: int) -> None:
        """
        Move XY to hover over a specific well in a bed.
        Z remains at SAFE_Z.
        
        Args:
            bed: Bed number
            well: Well number (1-indexed)
        """
        self._ensure_conn()
        if bed not in self.bed_layouts:
            raise ValueError(f"Bed {bed} not configured. Call set_bedlayout() first.")
        
        bed_layout = self.bed_layouts[bed]
        well_obj = bed_layout.get_well(well)
        x = well_obj.get_x()
        y = well_obj.get_y()
        
        print(f"Moving to Bed {bed}, Well {well} at X={x:.2f}, Y={y:.2f}")
        self.move_xy(x, y)
    
    def get_well_z(self, bed: int, well: int) -> float:
        """Get the Z coordinate for a specific well."""
        if bed not in self.bed_layouts:
            raise ValueError(f"Bed {bed} not configured.")
        return self.bed_layouts[bed].get_well(well).get_z()
    
    def status(self) -> str:
        """Return a string representing the current x, y and z status of the liquid handler."""
        try:
            x, y = self.get_xy()
            z = self.get_z()
            return f"Ender3 Status - X: {x:.2f}, Y: {y:.2f}, Z: {z:.2f}"
        except Exception as e:
            return f"Ender3 Status - Error: {e}"
    
    # movement methods can assert connectivity using Device.connected
    def _ensure_conn(self) -> None:
        if not self.connected:
            # If low-level serial is open, sync the flag and continue.
            if getattr(self, "s", None) and self.s.is_open:
                self._connected = True
            else:
                raise RuntimeError("Ender3 not connected. Call connect() first.")

# ============================== USAGE EXAMPLE ==============================

if __name__ == "__main__":
    # Use the subclass exactly like the parent, plus any helpers you add.
    e = Ender3LiquidHandler(port="COM23", baud=115200, timeout=2, verbose=False)
    try:
        e.connect()
        e.home(lift_mm=130)
        e.move_xy(x=41.5, y=41.4)
        e.move_z(z=100)
        e.move_z(z=130)
        e.move_xy(x=41.5, y=83)
        e.move_z(z=100)
        e.move_z(z=130)
        e.home(lift_mm=130)
        e.location()
    finally:
        e.close()