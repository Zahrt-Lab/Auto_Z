# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

# pumps.py
from __future__ import annotations
import abc

class Pump(abc.ABC):
    """Abstract high-level interface for pumps used within the lab space.

    Units:
    - flow_rate: microliters per minute (µL/min)
    - volume: microliters (µL)

    Implementations must implement the Device lifecycle methods and set
    `self._connected = True` on successful `connect()`.
    """

    @abc.abstractmethod
    def connect(self) -> None:
        """Connect to the pump device.""" 

    @abc.abstractmethod
    def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Aspirate `volume_ul` (µL) at `flow_rate_ul_min` (µL/min)."""

    @abc.abstractmethod
    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Dispense `volume_ul` (µL) at `flow_rate_ul_min` (µL/min)."""

    @abc.abstractmethod
    def set_flow_rate(self, flow_rate_ul_min: float) -> None:
        """Set a default flow rate (µL/min) for subsequent operations."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop any ongoing aspiration/dispense operation promptly."""

    @abc.abstractmethod
    def status(self) -> str:
        """Return a string representing the current status of the pump."""

    @abc.abstractmethod
    def close(self) -> None:
        """Convenience: shutdown the pump (default: call `disconnect()`)."""
