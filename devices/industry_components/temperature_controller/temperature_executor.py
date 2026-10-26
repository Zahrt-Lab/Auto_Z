# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
Executor for temperature controller actions (set_temperature, get_temperature, wait_convergence).
Includes the blocking convergence helper that polls until the setpoint is stable.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Callable

from devices.industry_components.temperature_controller.temperature_controller import (
    TemperatureController,
)
from methods.parameter_parser import parse_params

LogCallback = Callable[[str, str, str, str, str], None]


class TemperatureExecutor:
    """Executes CSV method actions for temperature controller devices."""

    def __init__(self, log_callback: LogCallback, continue_flag_getter: Callable[[], bool]) -> None:
        """
        Parameters:
            log_callback: Function to log an action row (component, action, params, output).
            continue_flag_getter: Callable returning bool. False triggers an abort.
        """
        self.log_to_csv: LogCallback = log_callback
        self._continue_experiment_getter: Callable[[], bool] = continue_flag_getter

    def execute(
        self,
        action: str,
        params: str,
        component: str,
        temp_control: TemperatureController,
    ) -> None:
        """Route action string to the appropriate temperature controller method."""

        if action == "set_temperature":
            temp = parse_params(params).get("temp")
            temp_control.set_temperature(temp)
            self.log_to_csv(
                component, action, params, f"Temperature controller set to {temp}°C"
            )

        elif action == "get_temperature":
            current_temp = temp_control.get_temperature()
            self.log_to_csv(
                component, action, params, f"Current temperature: {current_temp}°C"
            )

        elif action == "wait_convergence":
            target_temp, tolerance, duration = (
                parse_params(params).get("target_temp"),
                parse_params(params).get("tolerance"),
                parse_params(params).get("duration"),
            )

            self.log_to_csv(
                component,
                action,
                params,
                f"Waiting for temperature to converge to {target_temp}±{tolerance}°C "
                f"for {duration}s",
            )

            converged = self._wait_temperature_convergence(
                temp_control, target_temp, tolerance, duration, component
            )

            if converged:
                self.log_to_csv(
                    component,
                    action,
                    params,
                    f"Temperature converged to {target_temp}±{tolerance}°C",
                )
            else:
                self.log_to_csv(
                    component,
                    action,
                    params,
                    "Warning: Temperature convergence interrupted or failed",
                )

        else:
            self.log_to_csv(
                component,
                action,
                params,
                f"Error: Unknown action '{action}' for temperature controller",
            )

    def _wait_temperature_convergence(
        self,
        temp_control: TemperatureController,
        target_temp: float,
        tolerance: float,
        duration: float,
        component: str,
    ) -> bool:
        """
        Poll until temperature stays within ±tolerance of target for `duration` seconds.
        Checks every 5 seconds. Returns True if converged, False if aborted.
        """
        check_interval = 5.0
        stable_start_time = None

        while True:
            if not self._continue_experiment_getter():
                print("Temperature convergence wait interrupted by stop signal")
                return False

            try:
                current_temp = temp_control.get_temperature()
                temp_diff = abs(current_temp - target_temp)
                in_range = temp_diff <= tolerance

                timestamp = datetime.now().strftime("%H:%M:%S")
                print(
                    f"[{timestamp}] {component}: Current={current_temp:.1f}°C, "
                    f"Target={target_temp}±{tolerance}°C, Diff={temp_diff:.1f}°C"
                )

                if in_range:
                    if stable_start_time is None:
                        stable_start_time = time.time()
                        print(
                            f"[{timestamp}] Temperature entered target range, "
                            f"waiting {duration}s for stability..."
                        )
                    else:
                        elapsed_stable = time.time() - stable_start_time
                        remaining = duration - elapsed_stable
                        if elapsed_stable >= duration:
                            print(
                                f"[{timestamp}] Temperature stable for {duration}s - CONVERGED"
                            )
                            return True
                        else:
                            print(
                                f"[{timestamp}] Temperature stable for {elapsed_stable:.1f}s "
                                f"(need {remaining:.1f}s more)"
                            )
                else:
                    if stable_start_time is not None:
                        print(
                            f"[{timestamp}] Temperature left target range, resetting timer"
                        )
                    stable_start_time = None

                time.sleep(check_interval)

            except Exception as e:
                print(f"Error reading temperature: {e}")
                self.log_to_csv(component, "wait_convergence", "", f"Error: {e}")
                time.sleep(check_interval)
