# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# All rights reserved.
# ------------------------------------------------------------------------------

from abc import ABC, abstractmethod


class DH2000Controller(ABC):
    """Abstract interface for DH-2000 broadband light source controllers."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def shutter_open(self) -> None: ...

    @abstractmethod
    def shutter_close(self) -> None: ...

    @abstractmethod
    def halogen_toggle(self) -> None: ...

    @abstractmethod
    def deuterium_toggle(self) -> None: ...

    @abstractmethod
    def status(self) -> dict: ...

    @abstractmethod
    def safe_shutdown(self) -> None: ...