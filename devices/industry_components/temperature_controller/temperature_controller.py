# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""Abstract base class for temperature controller components."""

from __future__ import annotations

import abc
from typing import Any


class TemperatureController(abc.ABC):
    """
    Abstract high-level interface for TemperatureController used within the lab space.
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
    def status(self) -> Any:
        """Return the current status of the temperature controller (str or dict)."""

    @abc.abstractmethod
    def close(self) -> None:
        """Convenience: shutdown the temperature controller (default: call `disconnect()`)."""

    @abc.abstractmethod
    def safe_shutdown(self, success: bool) -> None:
        """Device-specific state cleanup called before close() during shutdown."""
