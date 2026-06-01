# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Executor for PhotoReactor (MirrorBox365nm) actions.
Actions: set_dimmer, status, read_temperature.
"""

from __future__ import annotations

from typing import Callable

from devices.custom_components.photo_reactor.photo_reactor_base import PhotoReactor
from methods.parameter_parser import parse_params

LogCallback = Callable[[str, str, str, str, str], None]


class PhotoReactorExecutor:
    """Executes General Methods actions for PhotoReactor devices."""

    def __init__(self, log_callback: LogCallback) -> None:
        """
        Parameters:
            - log_callback: Function to log an action row (component, action, params, output).
        """
        self.log_to_csv: LogCallback = log_callback

    def execute(
        self, action: str, params: str, component: str, mirror_box: PhotoReactor
    ) -> None:
        """Route action string to the appropriate PhotoReactor method."""
        try:
            if action == "set_dimmer":
                dimmer_value = int(parse_params(params).get("value"))
                response = mirror_box.set_dimmer(dimmer_value)
                self.log_to_csv(component, action, params, response or "OK")

            elif action == "status":
                status = mirror_box.status()
                notes = (
                    f"L1={'ON' if status.get('light1_on') else 'OFF'} "
                    f"L2={'ON' if status.get('light2_on') else 'OFF'} "
                    f"TC3={status.get('temp_light1_c')}C "
                    f"TC4={status.get('temp_light2_c')}C"
                )
                self.log_to_csv(component, action, params, str(status), notes=notes)

            elif action == "read_temperature":
                temp_data = mirror_box.read_temperature_stream()

                if "error" in temp_data:
                    self.log_to_csv(
                        component, action, params, f"Error: {temp_data['error']}"
                    )
                else:
                    notes = (
                        f"TC3={temp_data.get('temp_light1_c')}C "
                        f"TC4={temp_data.get('temp_light2_c')}C"
                    )

                    self.log_to_csv(
                        component, action, params, str(temp_data), notes=notes
                    )

            else:
                self.log_to_csv(
                    component,
                    action,
                    params,
                    f"Error: Unknown PhotoReactor action '{action}'",
                )
                raise ValueError(f"Unknown PhotoReactor action '{action}'")

        except Exception as e:
            self.log_to_csv(component, action, params, f"Error: {e}")
            raise
