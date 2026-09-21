# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Andrew Zahrt
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

# peristaltic_pumps.py
from __future__ import annotations
import abc
from devices.industry_components.pumps.pumps import Pump

class PeristalticPump(Pump, abc.ABC):
    """Abstract high-level interface for pumps used within the lab space.

    Units:
    - flow_rate: microliters per minute (µL/min)
    - volume: microliters (µL)

    Implementations must implement the Device lifecycle methods and set
    `self._connected = True` on successful `connect()`.
    """

    @abc.abstractmethod
    def set_number_of_channels(self, num_channels: int) -> None:
        """Set the number of channels for the peristaltic pump."""

    @abc.abstractmethod
    def get_number_of_channels(self) -> int:
        """Get the current number of channels configured for the peristaltic pump."""
        
    @abc.abstractmethod
    def set_channel(self, num_channels: int) -> None:
        """Set the active channel for the peristaltic pump."""

    @abc.abstractmethod
    def set_tubing_size(self, tubing_size_mm: float) -> None:
        """Set the tubing size (in mm) for the peristaltic pump."""

    @abc.abstractmethod
    def get_channel(self) -> int:
        """Get the active channel number for the peristaltic pump."""

    @abc.abstractmethod
    def get_tubing_size(self) -> float:
        """Get the current tubing size (in mm) configured for the peristaltic pump."""

    @abc.abstractmethod
    def aspirate(self, flow_rate_ul_min: float, volume_ul: float, channel: int) -> None:
        """Aspirate the given volume at the specified flow rate on the given channel."""

    @abc.abstractmethod
    def dispense(self, flow_rate_ul_min: float, volume_ul: float, channel: int) -> None:
        """Dispense the given volume at the specified flow rate on the given channel."""

