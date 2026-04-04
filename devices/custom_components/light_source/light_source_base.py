# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# All rights reserved.
# ------------------------------------------------------------------------------

from abc import ABC, abstractmethod


class PhotoReactor(ABC):
    """Abstract interface for custom light source components."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def set_dimmer(self, value: int) -> None: ...

    @abstractmethod
    def status(self) -> dict: ...

    @abstractmethod
    def read_temperature_stream(self) -> dict: ...