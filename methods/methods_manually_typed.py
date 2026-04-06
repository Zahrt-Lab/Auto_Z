# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Instrument Orchestrator for Software packages
Handles loading configuration, initializing instruments, and managing connections.

To add a new device that follows our abstract base classes: edit methods/device_registry.toml — no changes needed here.
"""

import pandas as pd
import time
from datetime import datetime
from pathlib import Path

# Import helper modules
from .experiment_logger import ExperimentLogger
from .status_monitor import StatusMonitor
from .instrument_manager import InstrumentManager
from .device_executors import DeviceExecutor

from devices.industry_components.liquid_handlers.liquid_handlers import LiquidHandler
from devices.industry_components.pumps.pumps import Pump
from devices.industry_components.valves.valves import Valves
from devices.industry_components.temperature_controller.temperature_controller import TemperatureController
from devices.industry_components.syringe_pumps.syringe_pumps import SyringePump
from devices.industry_components.uv_detectors.dh2000_base import DH2000Controller
from devices.industry_components.uv_detectors.uv_detector_base import UVDetector
# TODO : Rename All directories and file names of light source to photo_reactor to avoid confusion
from devices.custom_components.light_source.light_source_base import PhotoReactor

class GeneralExperimentMethod:
    """
    Orchestator for running experiments with any combination of devices
    
    Used to construct experiment workflows 
    """

    def __init__(self,
                 input_file,
                 instrument_config_file,
                 output_dir = Path("experiment_output" / "outputs"),
                 output_file = "Experimental_Log",
                 delay = 0.5,
                 status_update_interval = 30,
                 instrument_control_file = Path("experiment_output" / "instrument_control.txt"),
                 dh2000_control_file = Path("experiment_output" / "dh2000_light_source_control.txt")
    ):
        """
        Initializes the GeneralExperimentMethod with the provided configuration.
        
        Parameters:
        - input_file: Path to the input file for the experiment of what actions to perform.
        - instrument_config_file: Path to the instrument configuration file that specifies which devices to connect.
        - output_dir: Directory for experiment output files.
        - output_file: Name of the experimental log file.
        - delay: Delay between operations.
        - status_update_interval: Interval for status updates.
        - instrument_control_file: Path to the instrument control file.
        - dh2000_control_file: Path to the DH2000 light source control file.
        """

        self.method = pd.read_csv(input_file)
        self.delay = delay # Delay between when executing instrument actions.
        self.status_interval = status_update_interval # Seconds between status updates
        self.instrument_control_file = instrument_control_file # Instrument to stop all instruments
        self.dh2000_control_file = dh2000_control_file # File path to control safe shutdown of DH2000

        # Initializes the experiment logger
        self.logger = ExperimentLogger(input_file, output_dir, output_file)

        # Initializes control files to True at the start of each experiment run
        ExperimentLogger.initialize_control_file(self.instrument_control_file)
        ExperimentLogger.initialize_control_file(self.dh2000_control_file)

        # Dictionary to store bed layouts for liquid handlers
        self.bed_layouts = {}

        # Initializes the instrument manager
        self.instrument_manager = InstrumentManager(
            instrument_config_file=instrument_config_file,
            experiment_subdir=self.logger.experiment_subdir
        )

        # TODO: What does this do exactly? Its not clear currently
        for attr_name, instrument in self.instrument_manager.instruments.items():
            setattr(self, attr_name, instrument)

        # Give DH2000 instance their control file path so they own the skip logic
        for device in self.instrument_manager.instruments.values():
            if isinstance(device, DH2000Controller):
                device.control_file_path = self.dh2000_control_file        

        # Control flag for experiment execution
        self._continue_experiment = True

        # Initializes Device Exector
        self.executor = DeviceExecutor(
            bed_layouts=self.bed_layouts,
            log_callback=self.log_to_csv,
            start_time=datetime.now(),
            continue_flag_getter=self.get_continue_flag
        )

        # Initialize status monitor
        self.status_monitor = StatusMonitor(
            instrument_manager=self.instrument_manager,
            status_log_filename=self.logger.status_log_filename,
            status_interval=self.status_interval,
            start_time=self.logger.start_time,
            instrument_control_file=self.instrument_control_file,
            log_callback=self.log_to_csv,
            continue_flag_getter=self.get_continue_flag
        )

        # The role of this script is to log all the experimental actions to a csv file 
        def log_to_csv(self, component, action, params, output, notes =""):
            """Log experimental data to CSV via the ExperimentLogger."""
            self.logger.log_to_csv(component, action, params, output, notes)

        def _set_continue_flag(self, value: bool):
            """Set the continue experiment flag."""
            self._continue_experiment = value

        def _check_continue_flag(self, path: str) -> bool:
            """Check control flag. Delegated to ExperimentLogger"""
            return ExperimentLogger.check_continue_flag(path)
        
        def start_status_monitoring(self):
            """Start the status monitor in a separate thread."""
            self.status_monitor.start()

        def stop_status_monitoring(self):
            """Stop the status monitor."""
            self.status_monitor.stop()

        def run_experiment(self):
            """Run the experiment by executing each row in the method CSV."""
            self.start_status_monitoring()
            for _, row in self.method.iterrows():
                if not self.get_continue_flag():
                    print("Experiment stopped by control flag.")
                    break
                try:
                    self.executor.execute_row(row)
                except Exception as e:
                    print(f"Error executing row {row}: {e}")
                time.sleep(self.delay)
            self.stop_status_monitoring()