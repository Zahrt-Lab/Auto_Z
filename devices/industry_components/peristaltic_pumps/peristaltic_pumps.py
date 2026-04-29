# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
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
    def set_channel(self, num_channels: int) -> None:
        """Set the number of channels for the peristaltic pump."""
    
    @abc.abstractmethod
    def set_tubing_size(self, tubing_size_mm: float) -> None:
        """Set the tubing size (in mm) for the peristaltic pump."""

    @abc.abstractmethod
    def get_channel(self) -> int:
        """Get the current number of channels configured for the peristaltic pump."""
    
    @abc.abstractmethod
    def get_tubing_size(self) -> float:
        """Get the current tubing size (in mm) configured for the peristaltic pump."""

