# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

# TODO : Need to program light source so it 
# TODO : Need to program methods so light source stays on at the end of each of method
# TODO : Need to incorporate the new tricontinental code as part of these commands

import os
import pandas as pd
import shutil
import time
import csv
from datetime import datetime
import threading
import sys
from pathlib import Path

from pumps.isametic_pump.isametic_pump import IsmaticPump

sys.path.insert(0, str(Path.cwd().parent.parent))
print(Path.cwd().parent)

# Import abstract base classes
from liquid_handlers.liquid_handlers import LiquidHandler
from pumps.pumps import Pump
from valves.valves import Valves
from temperature_controller.temperature_controller import TemperatureController
from syringe_pumps.syringe_pumps import SyringePump

# Import concrete implementations
from liquid_handlers.gx281.gx281 import GX281
from liquid_handlers.ender3_liquid_handler.ender3_liquid_handler import Ender3LiquidHandler
from liquid_handlers.bed_layout import BedLayout
from pumps.vici_m6_pump.vici_m6_pump import VICI_M6_Pumps
from pumps.isametic_pump.isametic_pump import IsmaticPump
from syringe_pumps.phd_ultra_pumps.phd_ultra_pumps import PhdUltraPump  
from valves.vici_valves.vici_valves import ViciValve
from temperature_controller.tc720.tc720 import TC720
# TODO can't find syringe pump and isamatic scripts and need to add this script later
#    PhdUltraPump  # Imports the commands for the harvard aparatus PhD Ultra syringe pumps

class GeneralExperimentMethod:
    def __init__(self, input_file, instrument_config_file, output_dir="Experimental_Data//Outputs",
                 output_file="Experimental_Log", delay=0.5, status_interval=60, 
                 control_file="control.txt"):
        # Load the CSV file
        self.input_file = input_file
        self.method = pd.read_csv(self.input_file)
        self.delay = delay  # Global delay parameter
        self.status_interval = status_interval  # Status check interval in seconds
        self.control_file = control_file  # File path to check for continue/stop signal

        # Initialize control file to True at the start of each experiment run
        self._initialize_control_file()

        # Dictionary to store bed layouts for each bed (1-6)
        self.bed_layouts = {}

        # The following will store all the experimental Data generated

        # Start time for experiment logging
        self.start_time = datetime.now()

        # Create output directory with the date of the experimental run
        date_str = self.start_time.strftime('%Y_%m_%d')
        self.output_dir = os.path.join(output_dir, date_str)
        os.makedirs(self.output_dir, exist_ok=True)  # Create directory if it doesn't exist

        # output_file will be used to create a subdirectory to story all the results
        self.experiment_subdir = os.path.join(self.output_dir,
                                              f"{self.start_time.strftime('%Y_%m_%d_%H-%M-%S')}_{output_file}")
        os.makedirs(self.experiment_subdir, exist_ok=True)  # Create the experiment subdirectory

        # Track instruments by name and type
        self.instruments = {}  # {attr_name: device_instance}
        self.instrument_types = {}  # {attr_name: InstrumentType}

        # Load instrument configuration and initialize devices
        self.instrument_config_file = instrument_config_file
        self.instrument_config = self.load_instrument_config(self.instrument_config_file)
        self.initialize_instruments(self.instrument_config)

        # track every launched pump job
        self._pump_threads = []

        # Status monitoring thread and control flag
        self._status_monitor_thread = None
        self._status_monitoring_active = False
        self._continue_experiment = True  # Flag to control experiment execution

        # Copy the input file to the experiment subdirectory
        shutil.copy(self.input_file, os.path.join(self.experiment_subdir, os.path.basename(self.input_file)))

        # Set log filename with timestamp
        self.log_filename = os.path.join(self.experiment_subdir,
                                         f"{self.start_time.strftime('%Y_%m_%d_%H-%M-%S')}_{output_file}.csv")

        # Initialize CSV log file with headers
        with open(self.log_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Time', 'Component', 'Action', 'Parameters', 'Output', "Notes"])

        # Set status log filename
        self.status_log_filename = os.path.join(self.experiment_subdir,
                                                f"{self.start_time.strftime('%Y_%m_%d_%H-%M-%S')}_Status_Log.csv")
        
        

    def load_instrument_config(self, config_file):
        """
        Loads the instrument configuration CSV and returns a DataFrame.
        The CSV should contain columns such as InstrumentType, DeviceNumber, Name, COMPort, OtherParams.
        """
        try:
            config_df = pd.read_csv(config_file)
            print(f"Loaded instrument configuration from {config_file}")
            return config_df
        except Exception as e:
            print(f"Error loading instrument configuration: {e}")
            return None

    def initialize_instruments(self, config_df):
        """
        Initializes instrument objects based on the configuration DataFrame.
        The instruments are stored in self.instruments and also set as attributes on self.
        """
        self.instruments = {}
        if config_df is None:
            print("No instrument configuration available.")
            return

        # Loop through each instrument defined in the config file
        for _, row in config_df.iterrows():
            instrument_type = row['InstrumentType'].strip()
            device_number = str(row['DeviceNumber']).strip() if not pd.isna(row['DeviceNumber']) else ""
            com_port = row['COMPort'].strip() if not pd.isna(row['COMPort']) else None
            # Use the provided output_dir for instruments that need it (e.g., UV detector)
            other_params = row['OtherParams'] if 'OtherParams' in row else None

            # Create a unique attribute name for the instrument (e.g., "GX281_1", "Pump_1")
            attr_name = f"{instrument_type}_{device_number}" if device_number else instrument_type

            # Instantiate the instrument based on its type
            if instrument_type == "GX281":
                obj = GX281(name=attr_name)
            elif instrument_type == "Ender3_Liquid_Handler":
                obj = Ender3LiquidHandler(port=com_port, name=attr_name)
            elif instrument_type == "VICI_M6_Pump":
                # VICI_M6_Pumps __init__ does not accept a 'name' kwarg; pass port only
                obj = VICI_M6_Pumps(port=com_port)
                # Attach a friendly name attribute for consistency with other instruments
                try:
                    obj.name = attr_name
                except Exception:
                    pass
            elif instrument_type == "Isametic":
                obj = IsmaticPump(port=com_port, name=attr_name)
            elif instrument_type == "PhdUltraPump":
                obj = PhdUltraPump(port=com_port, name=attr_name)
            # TODO current code only supports Vici valves, add other valve types as needed and make necessary changes to code
            elif instrument_type in ("Valve6Way", "Valve10Way", "Valve24Way"):
                # pick the right string for ViciValve
                valve_type = {
                    "Valve6Way": "6-way",
                    "Valve10Way": "10-way",
                    "Valve24Way": "24-way"
                }[instrument_type]
                # ViciValve __init__ does not accept a 'name' kwarg
                obj = ViciValve(port=com_port, valve_type=valve_type)
                # Attach a friendly name attribute for consistency with other instruments
                try:
                    obj.name = attr_name
                except Exception:
                    pass
            elif instrument_type == "Temperature":
                obj = TC720(port=com_port, name=attr_name)
            else:
                print(f"Unknown instrument type: {instrument_type}")
                continue

            # Store the instrument and its type
            self.instruments[attr_name] = obj
            self.instrument_types[attr_name] = instrument_type
            setattr(self, attr_name, obj)
            print(f"Initialized {attr_name} ({instrument_type}) on COM Port {com_port if com_port else 'N/A'}")
        
        # Connect all instruments after initialization
        self.connect_all_instruments()

    def connect_all_instruments(self):
        """Connect to all initialized instruments that have a connect() method."""
        for name, device in self.instruments.items():
            if hasattr(device, 'connect'):
                try:
                    device.connect()
                    print(f"Connected to {name}")
                except Exception as e:
                    print(f"Failed to connect to {name}: {e}")

    # The role of this script is to log all the experimental data to a csv to be recorded and plotted out in the future.
    def log_to_csv(self, component, action, params, output, notes=""):
        elapsed_time = round((datetime.now() - self.start_time).total_seconds(), 2)
        with open(self.log_filename, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([elapsed_time, component, action, params, output, notes])

    def _initialize_control_file(self):
        """
        Initialize the control file to 'True' at the start of each experiment run.
        This ensures experiments can run unless explicitly stopped.
        """
        try:
            with open(self.control_file, 'w', encoding='utf-8') as f:
                f.write('True')
            print(f"Control file '{self.control_file}' initialized to True")
        except Exception as e:
            print(f"Warning: Could not initialize control file {self.control_file}: {e}")

    def _check_continue_flag(self):
        """
        Check the control file for continue/stop signal.
        Returns True if experiment should continue, False if it should stop.
        File should contain 'True' or 'False' (case-insensitive).
        """
        try:
            if os.path.exists(self.control_file):
                with open(self.control_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip().lower()
                    if content == 'false':
                        return False
                    elif content == 'true':
                        return True
            # If file doesn't exist or contains invalid content, default to True (continue)
            return True
        except Exception as e:
            print(f"Warning: Could not read control file {self.control_file}: {e}")
            return True  # On error, continue experiment

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
            continue_flag = self._check_continue_flag()
            if not continue_flag:
                self._continue_experiment = False
                print(f"[{timestamp}] STOP signal received from {self.control_file}")
                self.log_to_csv("CONTROL", "stop_signal", f"file={self.control_file}", 
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

    def start_status_monitoring(self):
        """Start the background status monitoring thread."""
        if self._status_monitoring_active:
            print("Status monitoring already running")
            return
        
        self._status_monitoring_active = True
        self._status_monitor_thread = threading.Thread(target=self._status_monitor_worker, daemon=True)
        self._status_monitor_thread.start()

    def stop_status_monitoring(self):
        """Stop the background status monitoring thread."""
        if not self._status_monitoring_active:
            return
        
        self._status_monitoring_active = False
        if self._status_monitor_thread and self._status_monitor_thread.is_alive():
            self._status_monitor_thread.join(timeout=5)
        self._status_monitor_thread = None

    def run_experiment(self):
        self.log_to_csv(0, "load_method", f"input={self.input_file}", f"Loading input file: {self.input_file}")

        # Start status monitoring before experiment begins
        self.start_status_monitoring()

        try:
            # Iterate through each row in the CSV file and execute the commands
            for index, row in self.method.iterrows():

                # Check if experiment should continue
                if not self._continue_experiment:
                    print("Experiment stopped by user request")
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
                    self.wait_for_pumps()
                    continue
                
                # Get the device instance from instruments
                device = self.instruments.get(component)
                if device is None:
                    self.log_to_csv(component, action, params, f"Error: Device '{component}' not found")
                    continue
                
                # Route to appropriate executor based on device type
                if isinstance(device, LiquidHandler):
                    self.execute_liquid_handler(action, params, component, device)
                elif isinstance(device, Pump):
                    self.execute_pump(action, params, component, device)
                elif isinstance(device, SyringePump):
                    self.execute_pump(action, params, component, device)
                elif isinstance(device, Valves):
                    self.execute_valve(action, params, component, device)
                elif isinstance(device, TemperatureController):
                    self.execute_temperature(action, params, component, device)
                else:
                    self.log_to_csv(component, action, params, f"Error: Unknown device type for '{component}'")

                time.sleep(self.delay)

            self.wait_for_pumps()
            self.stop_status_monitoring()
            self.close_all_connections()

        except:
            self.log_to_csv('', '', '', "Error: Experiment failed stopping exerpiment"
                                        "and closing connections to all instruments")
            self.stop_status_monitoring()
            self.close_all_connections()

    def execute_liquid_handler(self, action, params, component, liquid_handler: LiquidHandler):
        """Execute liquid handler actions using abstract interface methods."""
        if action == 'set_bedlayout':
            bed, rack_layout = self.extract_bed_rack_layout(params)
            # Check if liquid handler has set_bedlayout method (Ender3 does, GX281 may not)
            if hasattr(liquid_handler, 'set_bedlayout'):
                liquid_handler.set_bedlayout(bed, rack_layout)
            else:
                # Fallback to GeneralExperimentMethod's bed_layouts for GX281
                self.set_bedlayout(bed, rack_layout)
            self.log_to_csv(component, action, params, f"Setting bed {bed} to bed layout {rack_layout}")

        elif action == 'move_home':
            liquid_handler.home()
            self.log_to_csv(component, action, "", "Homing liquid handler")

        elif action == 'move_z_height':
            z_coord = self.extract_height(params)
            liquid_handler.move_z(z_coord)
            self.log_to_csv(component, action, params, f"Moving needle to z height {z_coord}")

        elif action == 'move_xy':
            bed, well = self.extract_bed_well(params)

            # Move needle up to safe height before XY movement to avoid collisions
            safe_z = liquid_handler.get_safe_z_height()
            liquid_handler.move_z(safe_z)
            #This timer was added to ensure there is enough time to move the needle up
            time.sleep(1)
            self.log_to_csv(component, action, params,
                            f"Moving liquid handler needle up before moving xy coordinates: {safe_z}")

            # Check if liquid handler has move_to_well (Ender3) or use coords (GX281)
            if hasattr(liquid_handler, 'move_to_well'):
                liquid_handler.move_to_well(bed, well)
            else:
                x, y = self.get_coords_for_bed_well(bed, well)
                liquid_handler.move_xy(x, y)
            self.log_to_csv(component, action, params, f"Moving liquid handler to bed {bed} well {well}")

        elif action == 'move_z':
            bed, well = self.extract_bed_well(params)

            # Check if liquid handler has get_well_z (Ender3) or use GeneralExperimentMethod's method
            if hasattr(liquid_handler, 'get_well_z'):
                z = liquid_handler.get_well_z(bed, well)
            else:
                z = self.get_z_for_bed_well(bed, well)
            liquid_handler.move_z(z)
            self.log_to_csv(component, action, params, f"Moving liquid handler needle on bed {bed} well {well}: z={z}")

        else:
            self.log_to_csv(component, action, params, f"Error: Unknown action '{action}' for liquid handler")

    def execute_pump(self, action, params, component, pump: Pump):
        """Execute pump actions using abstract interface methods."""
        # Handle select_syringe for SyringePump instances
        if action == "select_syringe":
            if not isinstance(pump, SyringePump):
                self.log_to_csv(component, action, params, f"Error: select_syringe is only available for SyringePump devices")
                return
            try:
                volume_ml = self.extract_syringe_volume(params)
                pump.select_syringe(volume_ml)
                self.log_to_csv(component, action, params, f"Selected syringe: {volume_ml} mL")
            except Exception as e:
                self.log_to_csv(component, action, params, f"Error selecting syringe: {e}")
            return

        # Extract parameters for aspirate/dispense
        flow_rate, volume = self.extract_flow_rate_and_volume(params)

        # Validate the action
        if action not in ("aspirate", "dispense"):
            self.log_to_csv(component, action, params, f"Error: Invalid action '{action}' – must be aspirate or dispense")
            return

        if flow_rate <= 0 or volume <= 0:
            self.log_to_csv(component, action, params, 
                            f"{action} skipped: volume={volume} µL, flow_rate={flow_rate} µL/min (must be > 0)")
            return

        est_time = abs(volume) / (abs(flow_rate) / 60)  # seconds

        # Worker that drives the pump
        def _pump_job():
            try:
                if action == "aspirate":
                    pump.aspirate(abs(flow_rate), abs(volume))
                else:  # dispense
                    pump.dispense(abs(flow_rate), abs(volume))
                
                self.log_to_csv(component, action, params,
                                f"{action} {abs(volume)} µL @ {flow_rate} µL/min",
                                notes=f"≈{est_time:.1f} s")
            except Exception as e:
                self.log_to_csv(component, action, params, f"Error in pump thread: {e}")

        # Launch async pump operation
        thread = threading.Thread(target=_pump_job, daemon=True)
        thread.start()
        self._pump_threads.append(thread)

        self.log_to_csv(component, action, params,
                        f"Started async {action}",
                        notes=f"exp. {est_time:.1f} s")

    def execute_valve(self, action, params, component, valve: Valves):
        """Execute valve actions using abstract interface methods."""
        if action == 'go_to_position':
            position = self.extract_position(params)
            if position is None:
                self.log_to_csv(component, action, params, f'Error: position parameter missing')
                return

            valve.go_to_position(position)
            self.log_to_csv(component, action, params, f"Moved valve to position {position}")

            current = valve.get_position()
            note = f"Valve now at position {current}"
            self.log_to_csv(component, 'check_position', '', current, notes=note)

        elif action == 'move_home':
            valve.move_home()
            self.log_to_csv(component, action, params, f"Homed valve")

            current = valve.get_position()
            note = f"Valve now at position {current}"
            self.log_to_csv(component, 'check_position', '', current, notes=note)

        else:
            self.log_to_csv(component, action, params, f"Error: Unknown action '{action}' for valve")

    def wait_for_pumps(self):
        """Block until every launched pump thread ends, then reset list."""
        for t in self._pump_threads:
            t.join()
        self.log_to_csv("SYNC", "wait_for_pumps", "", "All pumps finished")
        self._pump_threads.clear()  # ready for the next batch

    def execute_temperature(self, action, params, component, temp_ctrl: TemperatureController):
        """Execute temperature controller actions using abstract interface methods."""
        if action == 'set_temperature':
            temp = self.extract_temperature_value(params)
            temp_ctrl.set_temperature(temp)
            self.log_to_csv(component, action, params, f"Temperature controller set to {temp}°C")

        elif action == 'get_temperature':
            current_temp = temp_ctrl.get_temperature()
            self.log_to_csv(component, action, params, f"Current temperature: {current_temp}°C")

        elif action == 'wait_convergence':
            # Extract parameters: target_temp, tolerance (default 2), duration (default 120)
            param_dict = {key.strip(): float(value.strip()) for key, value in
                          (param.split('=') for param in params.split(','))}
            target_temp = param_dict['target_temp']
            tolerance = param_dict.get('tolerance', 2.0)  # ±2°C default
            duration = param_dict.get('duration', 120.0)  # 120 seconds (2 min) default
            
            self.log_to_csv(component, action, params, 
                           f"Waiting for temperature to converge to {target_temp}±{tolerance}°C for {duration}s")
            
            # Wait for temperature convergence
            converged = self._wait_temperature_convergence(
                temp_ctrl, target_temp, tolerance, duration, component
            )
            
            if converged:
                self.log_to_csv(component, action, params, 
                               f"Temperature converged to {target_temp}±{tolerance}°C")
            else:
                self.log_to_csv(component, action, params, 
                               f"Warning: Temperature convergence interrupted or failed")

        else:
            self.log_to_csv(component, action, params, f"Error: Unknown action '{action}' for temperature controller")

    def _wait_temperature_convergence(self, temp_ctrl: TemperatureController, 
                                      target_temp: float, tolerance: float, 
                                      duration: float, component: str) -> bool:
        """
        Wait until temperature stays within tolerance range for specified duration.
        Checks every 5 seconds.
        Returns True if converged, False if interrupted.
        """
        check_interval = 5.0  # seconds between temperature checks
        stable_start_time = None
        
        while True:
            # Check if experiment should continue
            if not self._continue_experiment:
                print(f"Temperature convergence wait interrupted by stop signal")
                return False
            
            try:
                current_temp = temp_ctrl.get_temperature()
                temp_diff = abs(current_temp - target_temp)
                in_range = temp_diff <= tolerance
                
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"[{timestamp}] {component}: Current={current_temp:.1f}°C, "
                      f"Target={target_temp}±{tolerance}°C, Diff={temp_diff:.1f}°C")
                
                if in_range:
                    # Temperature is in range
                    if stable_start_time is None:
                        # Just entered range
                        stable_start_time = time.time()
                        print(f"[{timestamp}] Temperature entered target range, "
                              f"waiting {duration}s for stability...")
                    else:
                        # Check how long we've been stable
                        elapsed_stable = time.time() - stable_start_time
                        remaining = duration - elapsed_stable
                        
                        if elapsed_stable >= duration:
                            # Converged!
                            print(f"[{timestamp}] Temperature stable for {duration}s - CONVERGED")
                            return True
                        else:
                            print(f"[{timestamp}] Temperature stable for {elapsed_stable:.1f}s "
                                  f"(need {remaining:.1f}s more)")
                else:
                    # Temperature out of range
                    if stable_start_time is not None:
                        print(f"[{timestamp}] Temperature left target range, resetting timer")
                    stable_start_time = None
                
                # Wait before next check
                time.sleep(check_interval)
                
            except Exception as e:
                print(f"Error reading temperature: {e}")
                self.log_to_csv(component, "wait_convergence", "", f"Error: {e}")
                time.sleep(check_interval)

    def set_bedlayout(self, bed, rack_layout):
        """Set the layout for a specific bed with the given rack_layout."""
        bed_layout = BedLayout(bed_number=bed, rack_layout=rack_layout)
        self.bed_layouts[bed] = bed_layout
        print(f"Bed {bed} layout set with rack_layout {rack_layout}")

    # Helper functions to extract parameters from the parameter string
    def extract_bed_rack_layout(self, params):
        """Extract bed and rack_layout from params."""
        param_dict = {key.strip(): int(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return param_dict['bed'], param_dict['rack_layout']

    def extract_bed_well(self, params):
        """Extract bed and well from params."""
        param_dict = {key.strip(): int(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return int(param_dict['bed']), int(param_dict['well'])

    def extract_height(self, params):
        """Extract height from params."""
        param_dict = {key.strip(): int(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return param_dict['height']

    def extract_flow_rate_and_volume(self, params):
        """Extract flow_rate and volume from params (generic, no pump_id)."""
        param_dict = {key.strip(): float(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return param_dict['flow_rate'], param_dict['volume']

    def extract_position(self, params):
        """Extract position from params."""
        param_dict = {key.strip(): int(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return param_dict.get('position')

    def extract_temperature_value(self, params):
        """Extract temperature value from params."""
        param_dict = {key.strip(): float(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return param_dict['temp']

    def extract_syringe_volume(self, params):
        """Extract syringe volume (mL) from params."""
        param_dict = {key.strip(): float(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return param_dict['volume_ml']

    def get_coords_for_bed_well(self, bed, well):
        x = self.bed_layouts[bed].get_well(well).get_x()
        y = self.bed_layouts[bed].get_well(well).get_y()
        # Return the X and Y coordinates based on the bed and well
        return x, y

    def get_z_for_bed_well(self, bed, well):
        z = self.bed_layouts[bed].get_well(well).get_z()
        # Return Z coordinate based on the bed and well number
        return z  # Example; replace with actual logic

    def emergency_stop(self):
        """
        Emergency stop: stop all devices and close all serial connections immediately.
        Called when continue flag becomes False.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] EMERGENCY STOP - Stopping all devices and closing connections")
        
        # Stop all devices using their stop() method
        for name, device in self.instruments.items():
            if hasattr(device, 'stop') and callable(device.stop):
                try:
                    device.stop()
                    print(f"Stopped device: {name}")
                    self.log_to_csv(name, "emergency_stop", "", f"Device stopped at {timestamp}")
                except Exception as e:
                    print(f"Failed to stop {name}: {e}")
                    self.log_to_csv(name, "emergency_stop", "", f"Error stopping device: {e}")
        
        # Close all connections
        self.close_all_connections()
        
        print(f"[{timestamp}] Emergency stop complete")

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
                    print(f"Closed connection for {name}")
                except Exception as e:
                    print(f"Failed to close {name}: {e}")
