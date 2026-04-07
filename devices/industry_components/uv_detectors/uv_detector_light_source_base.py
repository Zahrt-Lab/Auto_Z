# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# All rights reserved.
# ------------------------------------------------------------------------------

from abc import ABC, abstractmethod


class uv_detector_light_source_base(ABC):
    """Abstract interface for uv detector light source controllers."""

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
    def safe_shutdown(self, success: bool) -> None: ...