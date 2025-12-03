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

class TemperatureController(abc.ABC):
    """Abstract high-level interface for TemperatureController used within the lab space.

    Units:
    - flow_rate: microliters per minute (µL/min)
    - volume: microliters (µL)

    Implementations must implement the Device lifecycle methods and set
    `self._connected = True` on successful `connect()`.
    """
    @abc.abstractmethod
    def connect(self) -> None:
        """Connect to the temperature controller device."""

    @abc.abstractmethod
    def set_temperature(self, temperature_celsius: float) -> None:
        """Set the target temperature in degrees Celsius."""

    @abc.abstractmethod
    def get_temperature(self) -> float:
        """Get the current temperature in degrees Celsius."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop any ongoing temperature control operation promptly."""

    @abc.abstractmethod
    def status() -> str:
        """Return a string representing the current status of the temperature controller."""

    @abc.abstractmethod
    def close(self) -> None:
        """Convenience: shutdown the temperature controller (default: call `disconnect()`)."""