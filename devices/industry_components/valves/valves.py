# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""Abstract base class for valve components."""

from __future__ import annotations
import abc


class Valves(abc.ABC):
    """Abstract high-level interface for Valves used within the lab space.

    Implementations must implement the Device lifecycle methods and set
    `self._connected = True` on successful `connect()`.
    """

    @abc.abstractmethod
    def connect(self) -> None:
        """Connect to the valve device."""

    @abc.abstractmethod
    def go_to_position(self, position: int) -> None:
        """Move to the specified position."""

    @abc.abstractmethod
    def get_position(self) -> int:
        """Get the current position."""

    @abc.abstractmethod
    def move_home(self) -> None:
        """Move to the home position."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop any ongoing valve operation promptly."""

    @abc.abstractmethod
    def status(self) -> str:
        """Return a string representing the current status of the valve."""

    @abc.abstractmethod
    def close(self) -> None:
        """Convenience: shutdown the valve (default: call `disconnect()`)."""

    @abc.abstractmethod
    def safe_shutdown(self, success: bool) -> None:
        """Device-specific state cleanup called before close() during shutdown."""
