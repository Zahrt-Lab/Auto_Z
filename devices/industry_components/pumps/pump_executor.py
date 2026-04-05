# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Executor for pump actions (aspirate, dispense, select_syringe).
Pump operations are asynchronous — use wait_for_pumps() to block until all finish.
"""

import threading
from devices.industry_components.pumps.pumps import Pump
from devices.industry_components.syringe_pumps.syringe_pumps import SyringePump


class PumpExecutor:
    """Executes CSV method actions for pump and syringe pump devices."""

    def __init__(self, log_callback):
        """
        Args:
            log_callback: Function to log an action row (component, action, params, output).
        """
        self.log_to_csv = log_callback
        self._pump_threads = []

    def execute(self, action: str, params: str, component: str, pump: Pump):
        """Route action string to the appropriate pump method."""
        from methods.parameter_parser import parse_params

        if action == "select_syringe":
            if not isinstance(pump, SyringePump):
                self.log_to_csv(component, action, params,
                                "Error: select_syringe is only available for SyringePump devices")
                return
            try:
                volume_ml = parse_params(params).get('volume_ml')
                pump.select_syringe(volume_ml)
                self.log_to_csv(component, action, params, f"Selected syringe: {volume_ml} mL")
            except Exception as e:
                self.log_to_csv(component, action, params, f"Error selecting syringe: {e}")
            return

        flow_rate = parse_params(params).get('flow_rate')
        volume = parse_params(params).get('volume')

        if action not in ("aspirate", "dispense"):
            self.log_to_csv(component, action, params,
                            f"Error: Invalid action '{action}' – must be aspirate or dispense")
            return

        if flow_rate <= 0 or volume <= 0:
            self.log_to_csv(component, action, params,
                            f"{action} skipped: volume={volume} µL, flow_rate={flow_rate} µL/min (must be > 0)")
            return

        est_time = abs(volume) / (abs(flow_rate) / 60)  # seconds

        def _pump_job():
            try:
                if action == "aspirate":
                    pump.aspirate(abs(flow_rate), abs(volume))
                else:
                    pump.dispense(abs(flow_rate), abs(volume))
                self.log_to_csv(component, action, params,
                                f"{action} {abs(volume)} µL @ {flow_rate} µL/min",
                                notes=f"≈{est_time:.1f} s")
            except Exception as e:
                self.log_to_csv(component, action, params, f"Error in pump thread: {e}")

        thread = threading.Thread(target=_pump_job, daemon=True)
        thread.start()
        self._pump_threads.append(thread)
        self.log_to_csv(component, action, params,
                        f"Started async {action}",
                        notes=f"exp. {est_time:.1f} s")

    def wait_for_pumps(self):
        """Block until every launched pump thread ends, then reset the thread list."""
        for t in self._pump_threads:
            t.join()
        self.log_to_csv("SYNC", "wait_for_pumps", "", "All pumps finished")
        self._pump_threads.clear()
