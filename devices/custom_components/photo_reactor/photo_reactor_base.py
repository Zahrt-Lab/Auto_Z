# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# All rights reserved.
# ------------------------------------------------------------------------------

"""Abstract base class for photoreactor light source components."""

from abc import ABC, abstractmethod

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
    def status(self) -> dict:
        """Returns the status of the photoreactor."""

    @abstractmethod
    def read_temperature_stream(self) -> dict:
        """Reads the temperature stream from the photoreactor."""

    @abstractmethod
    def safe_shutdown(self, success: bool) -> None:
        """Performs a safe shutdown of the photoreactor."""
