# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Status monitoring utilities for General Methods.

Performs montoring of key parameters of interest during an experiment run.
Used for dianostic purposes and to track instrument behavior over time.
"""

from __future__ import annotations

import csv
import time
import threading
from datetime import datetime
from typing import Any, Callable

from .experiment_logger import ExperimentLogger

LogCallback = Callable[[str, str, str, str, str], None]


class StatusMonitor:
    """Manages background status monitoring of instruments."""

    def __init__(
        self,
        instruments: dict[str, Any],
        status_log_filename: str,
        status_interval: int | float,
        start_time: datetime,
        instrument_control_file: str,
        log_callback: LogCallback,
        continue_flag_callback: Callable[[bool], None],
    ) -> None:
        """
        Initialize the status monitor.

        Parameters:
            instruments: Dictionary of instrument instances {name: device}
                        ex. {"Pump_1": <VICI M6 Pump object>, "Pump_2": <VICI M6 Pump object>}
            status_log_filename: Path to the status log CSV file
                        ex. "experiment_subdir/status_log.csv"
            status_interval: Time between status checks in seconds
                        ex. 60 for 1-minute intervals
            start_time: Experiment start time (datetime)
                        ex. datetime.now() at the start of the experiment
            instrument_control_file: Path to control file for stop signals
                        ex. "instrument_control.txt"
            log_callback: Function to call for logging (e.g., logger.log_to_csv)
                        ex. logger.log_to_csv
            continue_flag_callback: Function to set continue flag to False on stop
                        ex.

        Returns:
            None
        """
        self.instruments: dict[str, Any] = instruments
        self.status_log_filename: str = status_log_filename
        self.status_interval: int | float = status_interval
        self.start_time: datetime = start_time
        self.instrument_control_file: str = instrument_control_file
        self.log_callback: LogCallback = log_callback
        self.continue_flag_callback: Callable[[bool], None] = continue_flag_callback

        # Status monitoring thread and control flag
        self._status_monitor_thread: threading.Thread | None = None
        self._status_monitoring_active: bool = False

    def _status_monitor_worker(self) -> None:
        """Background worker that polls all instruments and logs their status."""
        # Initialize the status CSV with headers
        device_names = sorted(self.instruments.keys())

        # Keeps timestamp, elapsed_time(s), and the status of each device in columns.
        # ex. ["Timestamp", "Elapsed_Time_s", "Pump_1", "Pump_2", "PhotoReactor_1", ...]
        headers = ["Timestamp", "Elapsed_Time_s"] + device_names

        with open(
            self.status_log_filename, mode="w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.writer(file)
            writer.writerow(headers)

        print(
            "Status monitoring started:"
            f"interval={self.status_interval}s, devices={len(device_names)}"
        )

        # Monitoring loop
        while self._status_monitoring_active:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elapsed = round((datetime.now() - self.start_time).total_seconds(), 2)

            # Check control file for continue/stop signal
            # If True, continue monitoring; if False, signal to stop and log the event
            continue_flag = ExperimentLogger.check_continue_flag(
                self.instrument_control_file
            )

            if not continue_flag:
                self.continue_flag_callback(False)
                self.log_callback(
                    "CONTROL",
                    "stop_signal",
                    f"file={self.instrument_control_file}",
                    "Experiment stop requested by user",
                )
                # Don't break here - let run_experiment handle the shutdown

            # Collect status from all devices
            status_row = [timestamp, elapsed]
            for device_name in device_names:

                # This gets the device_instance object based on it's name within this dictionary
                # ex. device_name = "Pump_1" → device = self.instruments["Pump_1"] 
                device = self.instruments[device_name]
                
                try:
                    # Call the device's status() method
                    # each device class has it's own implementation of the status() method
                    status_result = device.status()
                    # If the status result is a dictionary, we convert it to a string for logging
                    if isinstance(status_result, dict):
                        status_str = status_result.get("msg", str(status_result))
                    else:
                        status_str = str(status_result)
                except Exception as e:
                    status_str = f"Error: {str(e)}"

                # Appends each individual device status to the status row list
                status_row.append(status_str)

            # Once the status row is compiled, the results are logged into the csv file
            try:
                with open(
                    self.status_log_filename, mode="a", newline="", encoding="utf-8"
                ) as file:
                    writer = csv.writer(file)
                    writer.writerow(status_row)
            except Exception as e:
                print(f"Failed to write status log: {e}")

            # This waits 1 seconds for he next status interval polling in the background thread
            # Once the total sleep time reaches the status interval (defalt 60s)
            for _ in range(int(self.status_interval)):
                if not self._status_monitoring_active:
                    break
                time.sleep(1)

        print("Status monitoring stopped")

    def start(self) -> None:
        """Start the background status monitoring thread."""
        if self._status_monitoring_active:
            print("Status monitoring already running")
            return

        self._status_monitoring_active = True
        self._status_monitor_thread = threading.Thread(
            target=self._status_monitor_worker, daemon=True
        )
        self._status_monitor_thread.start()

    def stop(self) -> None:
        """Stop the background status monitoring thread."""
        if not self._status_monitoring_active:
            return
        
        # This sets the flag to False, which signals the background thread to exit its loop
        self._status_monitoring_active = False

        # This waits for the background thread to finish, with a timeout to prevent hanging
        if self._status_monitor_thread and self._status_monitor_thread.is_alive():
            self._status_monitor_thread.join(timeout=5)
        self._status_monitor_thread = None
