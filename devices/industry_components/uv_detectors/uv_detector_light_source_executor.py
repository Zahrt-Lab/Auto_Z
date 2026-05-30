# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Executor for DH2000 light source actions.
Actions: shutter_open, shutter_close, halogen_toggle, deuterium_toggle, status, safe_shutdown.
"""

from devices.industry_components.uv_detectors.uv_detector_light_source_base import (
    uv_detector_light_source_base
)


class UvDetectorLightSourceExecutor:
    """Executes CSV method actions for the DH2000 deuterium/halogen light source."""

    def __init__(self, log_callback):
        """
        Args:
            log_callback: Function to log an action row (component, action, params, output).
        """
        self.log_to_csv = log_callback

    def execute(self, action: str, params: str, component: str, dh: uv_detector_light_source_base):
        """Route action string to the appropriate DH2000 method."""
        try:
            if action == "shutter_open":
                dh.shutter_open()
                self.log_to_csv(component, action, params, "OK")

            elif action == "shutter_close":
                dh.shutter_close()
                self.log_to_csv(component, action, params, "OK")

            elif action == "halogen_toggle":
                dh.halogen_toggle()
                self.log_to_csv(component, action, params, "OK")

            elif action == "deuterium_toggle":
                dh.deuterium_toggle()
                self.log_to_csv(component, action, params, "OK")

            elif action == "status":
                st = dh.status()
                self.log_to_csv(component, action, params, str(st),
                                notes="; ".join(st.get("arduino_output", [])))

            elif action == "safe_shutdown":
                dh.safe_shutdown()
                self.log_to_csv(component, action, params,
                                "Shutdown ensured (Shutter CLOSED, Lamps OFF)")

            else:
                self.log_to_csv(component, action, params,
                                f"Error: Unknown DH2000 action '{action}'")
                raise ValueError(f"Unknown DH2000 action '{action}'")

        except Exception as e:
            self.log_to_csv(component, action, params, f"Error: {e}")
            raise
