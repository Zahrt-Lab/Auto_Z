# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Andrew Zahrt
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
Executor for pump actions (aspirate, dispense, select_syringe, select_tubing).
Pump operations are asynchronous — use wait_for_pumps() to block until all finish.
"""

from __future__ import annotations

import threading
from typing import Callable

from devices.industry_components.pumps.pumps import Pump
from devices.industry_components.syringe_pumps.syringe_pumps import SyringePump
from devices.industry_components.peristaltic_pumps.peristaltic_pumps import (
    PeristalticPump,
)
from methods.parameter_parser import parse_params

LogCallback = Callable[[str, str, str, str, str], None]


# TODO: We never finished testing and validating peristaltic pump support, so we should remove it for now to avoid confusion.

class PumpExecutor:
    """Executes CSV method actions for pump and syringe pump devices."""

    def __init__(self, log_callback: LogCallback) -> None:
        """
        Parameters:
            log_callback: Function to log an action row (component, action, params, output).
        """
        self.log_to_csv: LogCallback = log_callback
        self._pump_threads: list[threading.Thread] = []
        self._active_pumps: list[Pump | SyringePump | PeristalticPump] = []

    def execute(self, action: str, params: str, component: str, pump: Pump) -> None:
        """Route action string to the appropriate pump method."""

        if action == "select_syringe":
            if not isinstance(pump, SyringePump):
                self.log_to_csv(
                    component,
                    action,
                    params,
                    "Error: select_syringe is only available for SyringePump devices",
                )
                return
            try:
                volume_ml = parse_params(params).get("volume_ml")
                pump.select_syringe(volume_ml)
                self.log_to_csv(
                    component, action, params, f"Selected syringe: {volume_ml} mL"
                )
            except Exception as e:
                self.log_to_csv(
                    component, action, params, f"Error selecting syringe: {e}"
                )
            return

        if action == "select_tubing":
            if not isinstance(pump, PeristalticPump):
                self.log_to_csv(
                    component,
                    action,
                    params,
                    "Error: select_tubing is only available for PeristalticPump devices",
                )
                return
            try:
                tubing_size_mm = parse_params(params).get("tubing_size_mm")
                pump.set_tubing_size(tubing_size_mm)
                self.log_to_csv(
                    component,
                    action,
                    params,
                    f"Selected tubing size: {tubing_size_mm} mm",
                )
            except Exception as e:
                self.log_to_csv(
                    component, action, params, f"Error selecting tubing size: {e}"
                )
            return

        flow_rate = parse_params(params).get("flow_rate")
        volume = parse_params(params).get("volume")
        if isinstance(pump, PeristalticPump) and action in ("aspirate", "dispense"):
            num_channels = parse_params(params).get("num_channels")
            if num_channels is not None:
                pump.set_channel(num_channels)

        if action not in ("aspirate", "dispense"):
            self.log_to_csv(
                component,
                action,
                params,
                f"Error: Invalid action '{action}' – must be aspirate or dispense",
            )
            return

        if flow_rate <= 0 or volume <= 0:
            self.log_to_csv(
                component,
                action,
                params,
                f"{action} skipped: volume={volume} µL, flow_rate={flow_rate} µL/min (must be > 0)",
            )
            return

        est_time = abs(volume) / (abs(flow_rate) / 60)  # seconds

        def _pump_job() -> None:
            try:
                if action == "aspirate":
                    if isinstance(pump, PeristalticPump):
                        pump.aspirate(
                            abs(flow_rate), abs(volume), int(pump.get_channel())
                        )
                    else:
                        pump.aspirate(abs(flow_rate), abs(volume))
                else:
                    if isinstance(pump, PeristalticPump):
                        pump.dispense(
                            abs(flow_rate), abs(volume), int(pump.get_channel())
                        )
                    else:
                        pump.dispense(abs(flow_rate), abs(volume))
                if isinstance(pump, PeristalticPump):
                    self.log_to_csv(
                        component,
                        action,
                        params,
                        f"{action} {abs(volume)} µL @ {flow_rate} µL/min on channel {pump.get_channel()}",
                        notes=f"≈{est_time:.1f} s",
                    )
                else:
                    self.log_to_csv(
                        component,
                        action,
                        params,
                        f"{action} {abs(volume)} µL @ {flow_rate} µL/min",
                        notes=f"≈{est_time:.1f} s",
                    )
            except Exception as e:
                self.log_to_csv(component, action, params, f"Error in pump thread: {e}")

        thread = threading.Thread(target=_pump_job, daemon=True)
        thread.start()
        self._pump_threads.append(thread)
        self._active_pumps.append(pump)
        self.log_to_csv(
            component,
            action,
            params,
            f"Started async {action}",
            notes=f"exp. {est_time:.1f} s",
        )

    def stop_all_pumps(self) -> None:
        """Send an immediate stop command to every pump with an active dispense thread."""
        for pump in self._active_pumps:
            try:
                pump.stop()
            except Exception:
                pass

    def wait_for_pumps(self) -> None:
        """Block until every launched pump thread ends, then reset the thread list."""
        for t in self._pump_threads:
            t.join()
        self.log_to_csv("SYNC", "wait_for_pumps", "", "All pumps finished")
        self._pump_threads.clear()
        self._active_pumps.clear()
