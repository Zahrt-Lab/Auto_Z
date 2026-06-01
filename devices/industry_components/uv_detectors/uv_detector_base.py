# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

"""Abstract base class for UV-Vis spectrometer detector components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class UVDetector(ABC):
    """Abstract interface for UV-Vis spectrometer detectors."""

    @abstractmethod
    def connect(self) -> None:
        """Connects to the UV-Vis spectrometer detector."""

    @abstractmethod
    def close(self) -> None:
        """Closes the connection to the UV-Vis spectrometer detector."""

    @abstractmethod
    def save_blank_spectrum(self) -> None:
        """Saves the blank spectrum for the UV-Vis spectrometer detector."""

    @abstractmethod
    def save_dark_spectrum(self) -> None:
        """Saves the dark spectrum for the UV-Vis spectrometer detector."""

    @abstractmethod
    def start_continuous(self) -> None:
        """Starts continuous spectrum acquisition for the UV-Vis spectrometer detector."""

    @abstractmethod
    def stop_continuous(self) -> None:
        """Stops continuous spectrum acquisition for the UV-Vis spectrometer detector."""

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """Returns the status of the UV-Vis spectrometer detector."""

    @abstractmethod
    def safe_shutdown(self, success: bool) -> None:
        """Performs a safe shutdown of the UV-Vis spectrometer detector."""
