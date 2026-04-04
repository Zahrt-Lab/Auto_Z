# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

# TODO : Need to incorporate the new tricontinental code as part of these commands

# TODO : Perform Final validation with this TODO list
# TODO : Need to incorporate the UV-detector into the methods code so that this calibration step can also be automated as well. 
# TODO : Need to incorporate new light source with tunable parameters to the AutoZahrt
# TODO : Need to program light source within methods so it stays on regardless of whether the light turns on and off again.
# TODO : Need to program methods so light source stays on at the end of each of method


import pandas as pd
import time
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path.cwd().parent.parent))

# Import helper modules
from .experiment_logger import ExperimentLogger
from .status_monitor import StatusMonitor
from .instrument_manager import InstrumentManager
from .device_executors import DeviceExecutor

# Import abstract base classes
from devices.industry_components.liquid_handlers.liquid_handlers import LiquidHandler
from devices.industry_components.pumps.pumps import Pump
from devices.industry_components.valves.valves import Valves
from devices.industry_components.temperature_controller.temperature_controller import TemperatureController
from devices.industry_components.syringe_pumps.syringe_pumps import SyringePump
from devices.industry_components.uv_detectors.dh2000_base import DH2000Controller
from devices.industry_components.uv_detectors.uv_detector_base import UVDetector
from devices.custom_components.light_source.light_source_base import LightSourceBase

# Import concrete implementations (needed for bed layout and shutdown)
from devices.industry_components.liquid_handlers.bed_layout import BedLayout


# TODO can't find syringe pump and isamatic scripts and need to add this script later
#    PhdUltraPump  # Imports the commands for the harvard aparatus PhD Ultra syringe pumps

class GeneralExperimentMethod:
    def __init__(self, input_file, instrument_config_file, output_dir="Experimental_Data//Outputs",
                 output_file="Experimental_Log", delay=0.5, status_interval=60, 
                 instrument_control_file="instrument_control.txt",
                 dh2000_light_source_control_file="dh2000_light_source_control.txt"):
        
        # Load the CSV file
        self.input_file = input_file
        self.method = pd.read_csv(self.input_file)
        self.delay = delay  # Global delay parameter
        self.status_interval = status_interval  # Status check interval in seconds
        self.instrument_control_file = instrument_control_file  # File path to check for continue/stop signal
        self.dh2000_light_source_control_file = dh2000_light_source_control_file  # File path for DH2000 light source control

        # Initialize experiment logger
        self.logger = ExperimentLogger(input_file, output_dir, output_file)
        self.start_time = self.logger.start_time
        self.output_dir = self.logger.output_dir
        self.experiment_subdir = self.logger.experiment_subdir
        self.log_filename = self.logger.log_filename
        self.status_log_filename = self.logger.status_log_filename

        # Initialize control files to True at the start of each experiment run
        ExperimentLogger.initialize_control_file(self.instrument_control_file)
        ExperimentLogger.initialize_control_file(self.dh2000_light_source_control_file)


        # Dictionary to store bed layouts for each bed (1-6)
        self.bed_layouts = {}

        # Initialize instrument manager and get instruments
        self.instrument_manager = InstrumentManager(
            instrument_config_file=instrument_config_file,
            experiment_subdir=self.experiment_subdir
        )
        self.instruments = self.instrument_manager.instruments
        self.instrument_types = self.instrument_manager.instrument_types
        
        # Set instruments as attributes on self for backward compatibility
        for attr_name, obj in self.instruments.items():
            setattr(self, attr_name, obj)

        # Control flag for experiment execution
        self._continue_experiment = True
        
        # Initialize device executor
        self.executor = DeviceExecutor(
            bed_layouts=self.bed_layouts,
            log_callback=self.log_to_csv,
            start_time=self.start_time,
            continue_flag_getter=lambda: self._continue_experiment
        )
        
        # Initialize status monitor
        self.status_monitor = StatusMonitor(
            instruments=self.instruments,
            status_log_filename=self.status_log_filename,
            status_interval=self.status_interval,
            start_time=self.start_time,
            instrument_control_file=self.instrument_control_file,
            log_callback=self.log_to_csv,
            continue_flag_callback=self._set_continue_flag
        )
        
        

    # The role of this script is to log all the experimental data to a csv to be recorded and plotted out in the future.
    def log_to_csv(self, component, action, params, output, notes=""):
        """Log experimental data to CSV. Delegated to ExperimentLogger."""
        self.logger.log_to_csv(component, action, params, output, notes)
            
    def _set_continue_flag(self, value: bool):
        """Set the continue experiment flag."""
        self._continue_experiment = value
    
    def _check_continue_flag(self, path: str) -> bool:
        """Check control flag. Delegated to ExperimentLogger."""
        return ExperimentLogger.check_continue_flag(path)

    def start_status_monitoring(self):
        """Start the background status monitoring thread."""
        self.status_monitor.start()

    def stop_status_monitoring(self):
        """Stop the background status monitoring thread."""
        self.status_monitor.stop()

    def run_experiment(self):
        self.log_to_csv("METHOD", "load_method", f"input={self.input_file}", f"Loading input file: {self.input_file}")

        # Start status monitoring before experiment begins
        self.start_status_monitoring()

        try:
            # Iterate through each row in the CSV file and execute the commands
            for index, row in self.method.iterrows():

                # Check if experiment should continue
                if not self._continue_experiment:
                    print("INITIALIZING EMERGENCY STOP")
                    self.log_to_csv("CONTROL", "emergency_stop", "", 
                                   "Experiment halted - emergency stop triggered")
                    self.emergency_stop()
                    return  # Exit immediately

                component = row['Component']
                action = row['Action']
                params = row['Parameters']
                notes = row['Notes']

                try:
                    self.delay = float(row['delay']) if 'delay' in row and not pd.isna(row['delay']) else 0.5
                except ValueError:
                    self.delay = 0.5  # Default delay if conversion fails

                if component.upper() == "SYNC" and action == "wait_for_pumps":
                    self.executor.wait_for_pumps()
                    continue
                
                # Get the device instance from instruments
                device = self.instruments.get(component)
                if device is None:
                    self.log_to_csv(component, action, params, f"Error: Device '{component}' not found")
                    continue
                
                # Route to appropriate executor based on device type
                if isinstance(device, LiquidHandler):
                    self.executor.execute_liquid_handler(action, params, component, device)
                elif isinstance(device, Pump):
                    self.executor.execute_pump(action, params, component, device)
                elif isinstance(device, SyringePump):
                    self.executor.execute_pump(action, params, component, device)
                elif isinstance(device, Valves):
                    self.executor.execute_valve(action, params, component, device)
                elif isinstance(device, TemperatureController):
                    self.executor.execute_temperature(action, params, component, device)
                elif isinstance(device, DH2000Controller):
                    self.executor.execute_dh2000(action, params, component, device)
                elif isinstance(device, UVDetector):
                    self.executor.execute_ocean_optics(action, params, component, device)
                elif isinstance(device, LightSourceBase):
                    self.executor.execute_mirror_box(action, params, component, device)
                else:
                    self.log_to_csv(component, action, params, f"Error: Unknown device type for '{component}'")

                time.sleep(self.delay)
            
            self.executor.wait_for_pumps()
            self.shutdown(success=True)

        except Exception as e:
            self.log_to_csv("SYSTEM", "run_experiment_error", "", f"FAILED: {e}")
            self.stop_status_monitoring()
            self.close_all_connections()

    # Execute methods - delegate to DeviceExecutor for actual implementation
    def execute_liquid_handler(self, action, params, component, liquid_handler: LiquidHandler):
        """Execute liquid handler actions. Delegated to DeviceExecutor."""
        self.executor.execute_liquid_handler(action, params, component, liquid_handler)

    def execute_pump(self, action, params, component, pump: Pump):
        """Execute pump actions. Delegated to DeviceExecutor."""
        self.executor.execute_pump(action, params, component, pump)

    def execute_valve(self, action, params, component, valve: Valves):
        """Execute valve actions. Delegated to DeviceExecutor."""
        self.executor.execute_valve(action, params, component, valve)

    def wait_for_pumps(self):
        """Wait for all pump operations to complete. Delegated to DeviceExecutor."""
        self.executor.wait_for_pumps()

    def execute_temperature(self, action, params, component, temp_ctrl: TemperatureController):
        """Execute temperature controller actions. Delegated to DeviceExecutor."""
        self.executor.execute_temperature(action, params, component, temp_ctrl)

    def execute_dh2000(self, action, params, component, dh: DH2000Controller):
        """Execute DH2000 light source actions. Delegated to DeviceExecutor."""
        self.executor.execute_dh2000(action, params, component, dh)

    def execute_ocean_optics(self, action, params, component, uv: UVDetector):
        """Execute Ocean Optics UV-Vis actions. Delegated to DeviceExecutor."""
        self.executor.execute_ocean_optics(action, params, component, uv)

    def execute_mirror_box(self, action, params, component, mirror_box: LightSourceBase):
        """Execute MirrorBox365nm actions. Delegated to DeviceExecutor."""
        self.executor.execute_mirror_box(action, params, component, mirror_box)

    def shutdown(self, success: bool):
        """
        success=True:
            - do NOT change DH2000 state (no toggles, no shutter commands)
            - optional: log status
        success=False:
            - if dh2000_light_source_control_file is True => force safe_shutdown()
            - if dh2000_light_source_control_file is False => do nothing to lights
        Always continues shutting down other devices even if DH2000 fails.
        """
        # Find DH2000 instance if present
        dh2000_name = None
        dh2000 = None
        for name, instance in self.instruments.items():
            if self.instrument_types.get(name) == "DH2000":
                dh2000_name = name
                dh2000 = instance
                break

        # --- DH2000 policy ---
        if dh2000 is not None:
            try:
                skip_dh2000 = self._check_continue_flag(self.dh2000_light_source_control_file)

                if success:
                    # Don't touch state. Just log it (optional but useful).
                    dh2000_status = dh2000.status()
                    self.log_to_csv(dh2000_name, "shutdown_success_noop", "", str(dh2000_status),
                                    notes="Success: leaving DH2000 state unchanged")
                else:
                    # Failure path: only act if the light control file is True
                    # True  => do NOT touch DH2000 (skip)
                    # False => force safe_shutdown()
                    if skip_dh2000:
                        self.log_to_csv(
                            dh2000_name,
                            "shutdown_failure_skipped",
                            "",
                            "SKIPPED",
                            notes=f"{self.dh2000_light_source_control_file}=True; leaving DH2000 unchanged"
                        )
                    else:
                        dh2000.safe_shutdown()
                        self.log_to_csv(
                            dh2000_name,
                            "shutdown_failure_safe",
                            "",
                            "OK",
                            notes="Failure: shutter closed + lamps off"
                        )

            except Exception as e:
                # retries happen inside safe_shutdown(); if still failing, log and continue
                self.log_to_csv(dh2000_name or "DH2000", "shutdown_error", f"success={success}", f"FAILED: {e}")
        # --- MirrorBox365nm: always dim to 255 (off) on shutdown ---
        for name, instance in self.instruments.items():
            if isinstance(instance, LightSourceBase):
                try:
                    instance.set_dimmer(255)
                    self.log_to_csv(name, "shutdown_set_dimmer", "value=255", "OK",
                                    notes="MirrorBox dimmed to 255 (off) at shutdown")
                except Exception as e:
                    self.log_to_csv(name, "shutdown_set_dimmer", "value=255", f"FAILED: {e}")

        # --- stop monitoring and close other instruments ---
        self.stop_status_monitoring()

        for name, instance in self.instruments.items():
            if hasattr(instance, 'close') and callable(instance.close):
                try:
                    instance.close()
                    self.log_to_csv("Close", "Connection closed at shutdown", name, "OK")
                except Exception as e:
                    self.log_to_csv("Close", f"Failed to close {name}: {e}", name, "FAILED")

    ############################################################################################

    def set_bedlayout(self, bed, rack_layout):
        """Set the layout for a specific bed with the given rack_layout."""
        bed_layout = BedLayout(bed_number=bed, rack_layout=rack_layout)
        self.bed_layouts[bed] = bed_layout
        self.log_to_csv("SetBedLayout", f"Bed {bed} layout set with rack_layout {rack_layout}", "", "OK")

    ###########################################################################################

    def emergency_stop(self):
        """
        Emergency stop: stop all devices and close all serial connections immediately.
        Called when continue flag becomes False.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_to_csv("EmergencyStop", f"[{timestamp}] EMERGENCY STOP - Stopping all devices and closing connections", "", "OK")
        
        # Stop all devices using their stop() method
        for name, device in self.instruments.items():
            if hasattr(device, 'stop') and callable(device.stop):
                try:
                    device.stop()
                    self.log_to_csv("EmergencyStop", f"Stopped device: {name}", "", "OK")
                    self.log_to_csv("EmergencyStop", f"Device stopped at {timestamp}", "", "OK")
                except Exception as e:
                    self.log_to_csv("EmergencyStop", f"Error stopping device: {e}", "", "FAILED")
        
        # Close all connections
        self.close_all_connections()
        
        print(f"[{timestamp}] EMERGENCY STOP COMPLETED")

    def close_all_connections(self):
        """
        Close serial connections on all initialized instruments.
        """
        # Stop status monitoring if it's running
        self.stop_status_monitoring()
        
        for name, inst in self.instruments.items():
            if hasattr(inst, 'close') and callable(inst.close):
                try:
                    inst.close()
                    self.log_to_csv("Close", f"Connection closed for {name}", name, "OK")
                except Exception as e:
                    self.log_to_csv("Close", f"Failed to close {name}: {e}", name, "FAILED")
