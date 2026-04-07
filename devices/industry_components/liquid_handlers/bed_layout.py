# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and David Polefrone are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

from devices.industry_components.liquid_handlers.wells import Well

_OFFSETS_PATH = Path(__file__).parent / "bed_offsets.toml"
_offsets_cache: Optional[dict] = None


def _load_offsets() -> dict:
    """Load bed_offsets.toml once and cache the result."""
    global _offsets_cache
    if _offsets_cache is None:
        with open(_OFFSETS_PATH, "rb") as f:
            _offsets_cache = tomllib.load(f)
    return _offsets_cache


class BedLayout():

    #The bed number has a fixed location of 1, 2, 3, 4, 5 and 6 which needs to be fixed in the code; user should not be able to edit this
    #The rack_layout the user should need to input to make sure they use the correct layout
    def __init__(self, bed_number, rack_layout, device_type='GX271'):

        #Sets the location bed number on the GX271 liquid handler
        # The far left is labeled 1 and far right is labeled 6
        self.bed_number=bed_number

        #Determines the layout of the racks, to feed into
        self.rack_layout=rack_layout

        self.device_type = device_type

        self.wells={}
        self.X=[]
        self.Y=[]
        self.Z = None

        self.coordinates=[]

        self.x_offset = []
        self.y_offset = 0.0

        self.num_wells=None

        # Load device-specific offsets from TOML (Ender3 rack 301 manages its own offsets)
        if rack_layout != 301:
            rack_key = f"rack_{rack_layout}"
            offsets = _load_offsets()
            if device_type not in offsets:
                raise ValueError(
                    f"Device type {device_type!r} not found in bed_offsets.toml. "
                    f"Known types: {list(offsets.keys())}"
                )
            if rack_key not in offsets[device_type]:
                raise ValueError(
                    f"Rack layout {rack_layout!r} not found for device {device_type!r} "
                    f"in bed_offsets.toml."
                )
            self.x_offset = offsets[device_type][rack_key]["x_offset"]
            self.y_offset = offsets[device_type][rack_key]["y_offset"]

        if rack_layout == 204:
            self.X = [0, 31.8, 63.6]
            self.Y = [103.4, 135.2, 166.9, 198.7, 230.4, 262.1, 293.9,325.6,357.4]
            self.Z = 60
            self.num_wells = 27
            [[self.coordinates.append([x + self.x_offset[self.bed_number - 1], y + self.y_offset]) for y in self.Y] for x in self.X]

        elif rack_layout==207:
            self.X = [0, 19.3, 38.6, 57.9, 77.2]
            self.Y = [95, 114.3, 133.6, 152.9, 172.2, 191.5, 210.8, 230.1, 249.4, 268.7, 288, 307.3, 326.6, 345.9, 365]
            self.Z = 115
            self.num_wells = 75
            [[self.coordinates.append([x + self.x_offset[self.bed_number - 1], y + self.y_offset]) for y in self.Y] for x in self.X]

        elif rack_layout==209:
            self.X = [0, 16.6, 33.2, 49.8, 66.4, 83]
            for i in range(0,16):
                self.Y.append(93 + 17.7 * i)
            self.Z = 86
            self.num_wells = 96
            self.stagger = 8.5
            for x_index, x in enumerate(self.X):
                for y in self.Y:
                    if x_index % 2 == 0:
                        self.coordinates.append([x + self.x_offset[self.bed_number - 1], y + self.y_offset])
                    else:
                        self.coordinates.append([x + self.x_offset[self.bed_number -1], y + self.y_offset + self.stagger])

        elif rack_layout == 301:
            # 20-vial rack for Ender3 liquid handler
            # 4 rows x 5 columns layout
            # Spacing: 40mm between vials in X, 45mm in Y
            # Starting position: X=20mm, Y=20mm
            self.X = [20, 60, 100, 140, 180]  # 5 columns, 40mm apart
            self.Y = [20, 65, 110, 155]        # 4 rows, 45mm apart
            self.Z = 100  # Z height when pipette tip is at vial opening
            self.num_wells = 20
            self.x_offset = [0]  # Ender3 only has one bed position
            [[self.coordinates.append([x, y]) for y in self.Y] for x in self.X]

        self.set_wells()

    # Can just fold this method into class initialization later on.
    def set_wells(self):

        # Assigns the bed layout as well as the x, y, and z positions of the liquid handler.
        if self.rack_layout in [204, 207, 209, 301]:
            print(f"Bed {self.bed_number} set to bed layout {self.rack_layout}")

        else:
            raise ValueError(f"Invalid bed layout type {self.rack_layout}. Currently supported types: 204, 207, 209, and 301.")



        for i in range(1, self.num_wells + 1):
            self.wells[i] = Well(i)

        for index, coordinate in enumerate(self.coordinates):
            self.wells[index+1].set_x(coordinate[0])
            self.wells[index+1].set_y(coordinate[1])
            self.wells[index+1].set_z(self.Z)

        return None

    def get_wells(self):
        return self.wells

    def get_well(self,index):
        return self.wells[index]
