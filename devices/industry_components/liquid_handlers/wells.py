# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Andrew Zahrt
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

from __future__ import annotations


class Well():

    def __init__(self, well_number: int, x: float | None = None, y: float | None = None, z: float | None = None) -> None:

        # Sets the location bed number on the GX281 liquid handler
        # Left to right: 1, 2, 3, 4, 5, 6. # IS THIS REALLY A BED NUMBER?
        self.well_number = well_number

        self.x = x
        self.y = y
        self.z = z

    def set_well_labels(self, well_number: int) -> None:
        self.well_number = well_number

    def get_well_labels(self) -> int:
        return self.well_number

    def set_x(self, x: float) -> None:
        self.x = x

    def get_x(self) -> float | None:
        return self.x

    def set_y(self, y: float) -> None:
        self.y = y

    def get_y(self) -> float | None:
        return self.y

    def set_z(self, z: float) -> None:
        self.z = z

    def get_z(self) -> float | None:
        return self.z