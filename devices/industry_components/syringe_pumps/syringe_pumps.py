# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""Abstract base class for syringe pump components."""

from __future__ import annotations
import abc


class SyringePump(abc.ABC):
    """Abstract high-level interface for Syringepumps used within the lab space.

    Units:
    - flow_rate: microliters per minute (µL/min)
    - volume: microliters (µL)
    """

    @abc.abstractmethod
    def connect(self) -> None:
        """Connect to the syringe pump device."""

    @abc.abstractmethod
    def select_syringe(self, volume_ml: float) -> None:
        """Select the syringe size (mL)."""

    @abc.abstractmethod
    def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Aspirate `volume_ul` (µL) at `flow_rate_ul_min` (µL/min)."""

    @abc.abstractmethod
    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Dispense `volume_ul` (µL) at `flow_rate_ul_min` (µL/min)."""

    @abc.abstractmethod
    def set_flow_rate(self, flow_rate_ul_min: float) -> None:
        """Set a default flow rate (µL/min) for subsequent operations."""

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop any ongoing aspiration/dispense operation promptly."""

    @abc.abstractmethod
    def status(self) -> str:
        """Return a string representing the current status of the pump."""

    @abc.abstractmethod
    def close(self) -> None:
        """Convenience: shutdown the pump (default: call `disconnect()`)."""

    @abc.abstractmethod
    def safe_shutdown(self, success: bool) -> None:
        """Device-specific state cleanup called before close() during shutdown."""
