# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

from __future__ import annotations

# Standard library imports
import pandas as pd
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Import helper modules
from .experiment_logger import ExperimentLogger
from .status_monitor import StatusMonitor
from .instrument_manager import InstrumentManager
from .device_executors import DeviceExecutor

# Import abstract base classes
from devices.industry_components.liquid_handlers.bed_layout import BedLayout
from devices.industry_components.liquid_handlers.liquid_handlers import LiquidHandler
from devices.industry_components.pumps.pumps import Pump
from devices.industry_components.valves.valves import Valves
from devices.industry_components.temperature_controller.temperature_controller import TemperatureController
from devices.industry_components.syringe_pumps.syringe_pumps import SyringePump
from devices.industry_components.uv_detectors.uv_detector_light_source_base import uv_detector_light_source_base
from devices.industry_components.uv_detectors.uv_detector_base import UVDetector
from devices.custom_components.photo_reactor.photo_reactor_base import PhotoReactor

class GeneralExperimentMethod:
    def __init__(
        self,
        input_file: str,
        instrument_config_file: str,
        output_dir: str = "Experimental_Data//Outputs",
        output_file: str = "Experimental_Log",
        delay: float = 0.5,
        status_interval: int | float = 60,
        instrument_control_file: str = "instrument_control.txt",
        dh2000_light_source_control_file: str = "dh2000_light_source_control.txt",
    ) -> None:
        
        # Load the CSV file
        self.input_file: str = input_file
        self.method: pd.DataFrame = pd.read_csv(input_file)
        self.delay: float = delay  # Global delay parameter
        self.status_interval: int | float = status_interval  # Status check interval in seconds
        self.instrument_control_file: str = instrument_control_file  # File path to check for continue/stop signal
        self.dh2000_light_source_control_file: str = dh2000_light_source_control_file  # File path for DH2000 light source control

        # Initialize experiment logger
        self.logger: ExperimentLogger = ExperimentLogger(input_file, output_dir, output_file)

        # Initialize control files to True at the start of each experiment run
        ExperimentLogger.initialize_control_file(self.instrument_control_file)
        ExperimentLogger.initialize_control_file(self.dh2000_light_source_control_file)


        # Dictionary to store bed layouts for each bed (1-6)
        self.bed_layouts: dict[int, BedLayout] = {}

        # Initialize instrument manager and get instruments
        self.instrument_manager: InstrumentManager = InstrumentManager(
            instrument_config_file=instrument_config_file,
            experiment_subdir=self.logger.experiment_subdir
        )
        
        # Set instruments as attributes on self for backward compatibility
        for attr_name, obj in self.instrument_manager.instruments.items():
            setattr(self, attr_name, obj)

        # Give DH2000 instances their control file path so they own the skip logic
        for device in self.instrument_manager.instruments.values():
            if isinstance(device, uv_detector_light_source_base):
                device.control_file_path = self.dh2000_light_source_control_file

        # Give UV detector instances the instrument control file path and convergence callback
        for device in self.instrument_manager.instruments.values():
            if isinstance(device, UVDetector):
                # UV detector needs access to the control file to check for stop signal during convergence monitoring
                device.instrument_control_file = self.instrument_control_file
                # If check_convergence_from_csv is True, the UV detector will call this callback when convergence is detected
                # This sets the continue flag for each worker thread to False, which triggers a clean stop of the experiment
                device.convergence_stop_callback = self._set_convergence_triggered

        # Control flag for experiment execution
        self._continue_experiment: bool = True
        self._convergence_triggered: bool = False

        # Initialize device executor
        self.executor: DeviceExecutor = DeviceExecutor(
            bed_layouts=self.bed_layouts,
            log_callback=self.log_to_csv,
            start_time=self.logger.start_time,
            continue_flag_getter=lambda: self._continue_experiment
        )
        
        # Initialize status monitor
        self.status_monitor: StatusMonitor = StatusMonitor(
            instruments=self.instrument_manager.instruments,
            status_log_filename=self.logger.status_log_filename,
            status_interval=self.status_interval,
            start_time=self.logger.start_time,
            instrument_control_file=self.instrument_control_file,
            log_callback=self.log_to_csv,
            continue_flag_callback=self._set_continue_flag
        )
        
        

    # The role of this script is to log all the experimental data to a csv to be recorded and plotted out in the future.
    def log_to_csv(self, component: str, action: str, params: str, output: str, notes: str = "") -> None:
        """Log experimental data to CSV. Delegated to ExperimentLogger."""
        self.logger.log_to_csv(component, action, params, output, notes)
            
    def _set_continue_flag(self, value: bool) -> None:
        """Set the continue experiment flag."""
        self._continue_experiment = value
        print(f"Continue flag set to: {self._continue_experiment}")

    def _set_convergence_triggered(self) -> None:
        """Called by UV detector on convergence — triggers a clean stop of the experiment and turns off all the pumps"""
        self._convergence_triggered = True
        self._continue_experiment = False
        self.executor.stop_all_pumps()

    def _check_continue_flag(self, path: str) -> bool:
        """Check control flag. Delegated to ExperimentLogger."""
        return ExperimentLogger.check_continue_flag(path)

    def start_status_monitoring(self) -> None:
        """Start the background status monitoring thread."""
        self.status_monitor.start()

    def stop_status_monitoring(self) -> None:
        """Stop the background status monitoring thread."""
        self.status_monitor.stop()

    def run_experiment(self) -> None:
        self.log_to_csv("METHOD", "load_method", f"input={self.input_file}", f"Loading input file: {self.input_file}")

        # Start status monitoring before experiment begins
        self.start_status_monitoring()

        try:
            # Iterate through each row in the CSV file and execute the commands
            for index, row in self.method.iterrows():

                # Check if experiment should continue
                if not self._continue_experiment:
                    if self._convergence_triggered:
                        print("UV CONVERGENCE REACHED — stopping experiment cleanly")
                        self.log_to_csv("CONTROL", "convergence_stop", "",
                                        "Experiment stopped — UV convergence reached")
                        self.convergence_stop()
                    else:
                        print("INITIALIZING EMERGENCY STOP")
                        self.log_to_csv("CONTROL", "emergency_stop", "",
                                        "Experiment halted - emergency stop triggered")
                        self.emergency_stop()
                    return  # Exit immediately

                try:
                    self.delay = float(row['delay']) if 'delay' in row and not pd.isna(row['delay']) else 0.5
                except ValueError:
                    self.delay = 0.5  # Default delay if conversion fails

                if row['Component'].upper() == "SYNC" and row['Action'] == "wait_for_pumps":
                    self.executor.wait_for_pumps()
                    continue
                
                # Get the device instance from instruments
                device = self.instrument_manager.instruments.get(row['Component'])
                if device is None:
                    self.log_to_csv(row['Component'], row['Action'], row['Parameters'], f"Error: Device '{row['Component']}' not found")
                    continue
                
                # Route to appropriate executor based on device type
                if isinstance(device, LiquidHandler):
                    self.executor.execute_liquid_handler(row['Action'], row['Parameters'], row['Component'], device)
                elif isinstance(device, Pump):
                    self.executor.execute_pump(row['Action'], row['Parameters'], row['Component'], device)
                elif isinstance(device, SyringePump):
                    self.executor.execute_pump(row['Action'], row['Parameters'], row['Component'], device)
                elif isinstance(device, Valves):
                    self.executor.execute_valve(row['Action'], row['Parameters'], row['Component'], device)
                elif isinstance(device, TemperatureController):
                    self.executor.execute_temperature(row['Action'], row['Parameters'], row['Component'], device)
                elif isinstance(device, uv_detector_light_source_base):
                    self.executor.execute_uv_detector_light_source(row['Action'], row['Parameters'], row['Component'], device)
                elif isinstance(device, UVDetector):
                    self.executor.execute_uv_detector(row['Action'], row['Parameters'], row['Component'], device)
                elif isinstance(device, PhotoReactor):
                    self.executor.execute_photo_reactor(row['Action'], row['Parameters'], row['Component'], device)
                else:
                    self.log_to_csv(row['Component'], row['Action'], row['Parameters'], f"Error: Unknown device type for '{row['Component']}'")

                time.sleep(self.delay)
            
            # TODO : Is self.executor.wait_for_pumps() need if we use it earlier in the method with the SYNC command?
            self.executor.wait_for_pumps()
            print("Wait_for_pumps completed")
            if self._convergence_triggered:
                self.convergence_stop()
            else:
                self.shutdown(success=True)

            # TODO: Add final line that plots all the status data of all the experiments for final visualization
            # self.status_monitor.plot_status_data()

        except Exception as e:
            self.log_to_csv("SYSTEM", "run_experiment_error", "", f"FAILED: {e}")
            self.shutdown(success=False)

    
    def _close_all_instruments(self) -> None:
        """Close serial connections for all instruments that have a close() method."""
        for name, instance in self.instrument_manager.instruments.items():
            if hasattr(instance, 'close') and callable(instance.close):
                try:
                    instance.close()
                    self.log_to_csv("Close", "Connection closed at shutdown", name, "OK")
                except Exception as e:
                    self.log_to_csv("Close", f"Failed to close {name}: {e}", name, "FAILED")

    def shutdown(self, success: bool) -> None:
        self.stop_status_monitoring()

        for name, device in self.instrument_manager.instruments.items():
            try:
                device.safe_shutdown(success)
                self.log_to_csv(name, "shutdown", f"success={success}", "OK")
            except Exception as e:
                self.log_to_csv(name, "shutdown_error", f"success={success}", f"FAILED: {e}")

        self._close_all_instruments()

    def emergency_stop(self) -> None:
        """
        Emergency stop: stop all devices and close all serial connections immediately.
        Called when continue flag becomes False.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_to_csv("EmergencyStop", f"[{timestamp}] EMERGENCY STOP - Stopping all devices and closing connections", "", "OK")

        for name, device in self.instrument_manager.instruments.items():
            if hasattr(device, 'stop') and callable(device.stop):
                try:
                    device.stop()
                    self.log_to_csv("EmergencyStop", f"Stopped device: {name}", "", "OK")
                except Exception as e:
                    self.log_to_csv("EmergencyStop", f"Error stopping device: {e}", "", "FAILED")

        # TODO: Does this turn off the light source of the DH2000 as well?
        self.shutdown(success=False)

        print(f"[{timestamp}] EMERGENCY STOP COMPLETED")

    def convergence_stop(self) -> None:
        """Clean stop triggered by UV convergence. Stops all devices and turns off DH2000 lamp."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_to_csv("ConvergenceStop", f"[{timestamp}] CONVERGENCE STOP - Stopping all devices", "", "OK")

        for name, device in self.instrument_manager.instruments.items():
            if hasattr(device, 'stop') and callable(device.stop):
                try:
                    device.stop()
                    self.log_to_csv("ConvergenceStop", f"Stopped device: {name}", "", "OK")
                except Exception as e:
                    self.log_to_csv("ConvergenceStop", f"Error stopping device: {e}", "", "FAILED")

        # Allow DH2000 safe_shutdown to proceed (control file starts as "True" = skip shutdown)
        try:
            Path(self.dh2000_light_source_control_file).write_text("False")
        except Exception as e:
            self.log_to_csv("ConvergenceStop", "dh2000_control_file_update_error", "", f"FAILED: {e}")

        self.shutdown(success=False)

        print(f"[{timestamp}] CONVERGENCE STOP COMPLETED")
