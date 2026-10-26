# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""Abstract base class for photoreactor light source components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

class PhotoReactor(ABC):
    """Abstract interface for custom light source components."""

    @abstractmethod
    def connect(self) -> None:
        """Connects to the light source of the photoreactor."""

    @abstractmethod
    def close(self) -> None:
        """Closes the connection to the light source of the photoreactor."""

    @abstractmethod
    def set_dimmer(self, value: int) -> None:
        """Sets the dimmer value for the light source."""

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """Returns the status of the photoreactor."""

    @abstractmethod
    def read_temperature_stream(self) -> dict[str, Any]:
        """Reads the temperature stream from the photoreactor."""

    @abstractmethod
    def safe_shutdown(self, success: bool) -> None:
        """Performs a safe shutdown of the photoreactor."""
