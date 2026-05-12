# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Status monitoring utilities for AUTO_ZAHRT.
Handles background monitoring of instruments and control file checking.
"""

import csv
import time
import threading
from datetime import datetime
from .experiment_logger import ExperimentLogger


class StatusMonitor:
    """Manages background status monitoring of instruments."""
    
    def __init__(self, instruments, status_log_filename, status_interval, 
                 start_time, instrument_control_file, log_callback, 
                 continue_flag_callback):
        """
        Initialize the status monitor.
        
        Args:
            instruments: Dictionary of instrument instances {name: device}
            status_log_filename: Path to the status log CSV file
            status_interval: Time between status checks in seconds
            start_time: Experiment start time (datetime)
            instrument_control_file: Path to control file for stop signals
            log_callback: Function to call for logging (e.g., logger.log_to_csv)
            continue_flag_callback: Function to set continue flag to False on stop
        """
        self.instruments = instruments
        self.status_log_filename = status_log_filename
        self.status_interval = status_interval
        self.start_time = start_time
        self.instrument_control_file = instrument_control_file
        self.log_callback = log_callback
        self.continue_flag_callback = continue_flag_callback
        
        # Status monitoring thread and control flag
        self._status_monitor_thread = None
        self._status_monitoring_active = False
    
    def _status_monitor_worker(self):
        """Background worker that polls all instruments and logs their status."""
        # Initialize the status CSV with headers
        device_names = sorted(self.instruments.keys())
        headers = ['Timestamp', 'Elapsed_Time_s'] + device_names
        
        with open(self.status_log_filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
        
        print(f"Status monitoring started: interval={self.status_interval}s, devices={len(device_names)}")
        
        # Monitoring loop
        while self._status_monitoring_active:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            elapsed = round((datetime.now() - self.start_time).total_seconds(), 2)
            
            # Check control file for continue/stop signal
            continue_flag = ExperimentLogger.check_continue_flag(self.instrument_control_file)
            if not continue_flag:
                self.continue_flag_callback(False)
                #TODO: Remove this print after debugging
                print(f"continue_flag in status monitor:{self.continue_flag_callback}")
                print(f"[{timestamp}] STOP signal received from {self.instrument_control_file}")
                self.log_callback("CONTROL", "stop_signal", f"file={self.instrument_control_file}",
                                "Experiment stop requested by user")
                # Don't break here - let run_experiment handle the shutdown
            
            # Collect status from all devices
            status_row = [timestamp, elapsed]
            for device_name in device_names:
                device = self.instruments[device_name]
                try:
                    # Call the device's status() method
                    status_result = device.status()
                    # Handle different return types (string or dict)
                    if isinstance(status_result, dict):
                        status_str = status_result.get('msg', str(status_result))
                    else:
                        status_str = str(status_result)
                except Exception as e:
                    status_str = f"Error: {str(e)}"
                
                status_row.append(status_str)
            
            # Write to CSV
            try:
                with open(self.status_log_filename, mode='a', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(status_row)
            except Exception as e:
                print(f"Failed to write status log: {e}")
            
            # Wait for next interval (check flag periodically for quick shutdown)
            for _ in range(int(self.status_interval)):
                if not self._status_monitoring_active:
                    break
                time.sleep(1)
        
        print("Status monitoring stopped")
    
    def start(self):
        """Start the background status monitoring thread."""
        if self._status_monitoring_active:
            print("Status monitoring already running")
            return
        
        self._status_monitoring_active = True
        self._status_monitor_thread = threading.Thread(target=self._status_monitor_worker, daemon=True)
        self._status_monitor_thread.start()
    
    def stop(self):
        """Stop the background status monitoring thread."""
        if not self._status_monitoring_active:
            return
        
        self._status_monitoring_active = False
        if self._status_monitor_thread and self._status_monitor_thread.is_alive():
            self._status_monitor_thread.join(timeout=5)
        self._status_monitor_thread = None
