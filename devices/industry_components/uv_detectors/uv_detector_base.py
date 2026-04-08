# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# All rights reserved.
# ------------------------------------------------------------------------------

from abc import ABC, abstractmethod


class UVDetector(ABC):
    """Abstract interface for UV-Vis spectrometer detectors."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def save_blank_spectrum(self) -> None: ...
    
    @abstractmethod
    def save_dark_spectrum(self) -> None: ...

    @abstractmethod
    def start_continuous(self) -> None: ...

    @abstractmethod
    def stop_continuous(self) -> None: ...

    @abstractmethod
    def status(self) -> dict: ...

    @abstractmethod
    def safe_shutdown(self, success: bool) -> None: ...