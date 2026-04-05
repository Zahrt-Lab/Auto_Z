# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Executor for valve actions (go_to_position, move_home).
"""

from devices.industry_components.valves.valves import Valves


class ValveExecutor:
    """Executes CSV method actions for valve devices."""

    def __init__(self, log_callback):
        """
        Args:
            log_callback: Function to log an action row (component, action, params, output).
        """
        self.log_to_csv = log_callback

    def execute(self, action: str, params: str, component: str, valve: Valves):
        """Route action string to the appropriate valve method."""
        from methods.parameter_parser import parse_params

        if action == 'go_to_position':
            position = parse_params(params).get('position')
            if position is None:
                self.log_to_csv(component, action, params, "Error: position parameter missing")
                return
            valve.go_to_position(position)
            self.log_to_csv(component, action, params, f"Moved valve to position {position}")
            current = valve.get_position()
            self.log_to_csv(component, 'check_position', '', current,
                            notes=f"Valve now at position {current}")

        elif action == 'move_home':
            valve.move_home()
            self.log_to_csv(component, action, params, "Homed valve")
            current = valve.get_position()
            self.log_to_csv(component, 'check_position', '', current,
                            notes=f"Valve now at position {current}")

        else:
            self.log_to_csv(component, action, params, f"Error: Unknown action '{action}' for valve")
