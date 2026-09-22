# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""Abstract base class for UV-Vis detector light source controllers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class uv_detector_light_source_base(ABC):
    """Abstract interface for uv detector light source controllers."""

    @abstractmethod
    def connect(self) -> None:
        """Connects to the light source controller of the UV-Vis detector."""

    @abstractmethod
    def close(self) -> None:
        """Closes the connection to the light source controller of the UV-Vis detector."""

    @abstractmethod
    def shutter_open(self) -> None:
        """Opens the shutter of the light source controller."""

    @abstractmethod
    def shutter_close(self) -> None:
        """Closes the shutter of the light source controller."""

    @abstractmethod
    def halogen_toggle(self) -> None:
        """Toggles the halogen light source on/off."""

    @abstractmethod
    def deuterium_toggle(self) -> None:
        """Toggles the deuterium light source on/off."""

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """Returns the status of the light source controller."""

    @abstractmethod
    def safe_shutdown(self, success: bool) -> None:
        """Performs a safe shutdown of the light source controller."""
