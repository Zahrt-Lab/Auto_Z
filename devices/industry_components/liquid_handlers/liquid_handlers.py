# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

"""Abstract base class for liquid handler robot components."""

from __future__ import annotations
import abc


class LiquidHandler(abc.ABC):
    """Abstract high-level interface for liquid handler robots (synchronous)."""

    @abc.abstractmethod
    def connect(self) -> None:
        """Connect to the liquid handler device."""

    @abc.abstractmethod
    def home(self) -> None:
        """Home the liquid handler (move axes to known reference)."""

    @abc.abstractmethod
    def move_xy(self, x: float, y: float) -> None:
        """Move the toolhead to X/Y coordinates (mm)."""

    @abc.abstractmethod
    def get_xy(self) -> tuple[float, float]:
        """Return the current X/Y position (mm)."""

    @abc.abstractmethod
    def move_z(self, z: float) -> None:
        """Move the toolhead to Z coordinate (mm)."""

    @abc.abstractmethod
    def get_z(self) -> float:
        """Return the current Z position (mm)."""

    @abc.abstractmethod
    def get_safe_z_height(self) -> float:
        """Return the safe Z height (mm) for the liquid handler."""

    @abc.abstractmethod
    def status(self) -> str:
        """Return a string representing the current x, y  and z status of the liquid handler."""

    @abc.abstractmethod
    def close(self) -> None:
        """Convenience: Safetly shutdowns the liquid handler (default: call `disconnect()`)."""
