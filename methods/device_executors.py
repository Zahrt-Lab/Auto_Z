# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Device execution utilities for AUTO_ZAHRT.
Handles execution of actions for all device types (liquid handlers, pumps, valves, temperature controllers, etc.).
"""

import time
import threading
from pathlib import Path

from .parameter_parser import ParameterParser

# Import abstract base classes
from liquid_handlers.liquid_handlers import LiquidHandler
from pumps.pumps import Pump
from valves.valves import Valves
from temperature_controller.temperature_controller import TemperatureController
from syringe_pumps.syringe_pumps import SyringePump
from uv_detectors.dh2000 import DH2000LightSource
from uv_detectors.uv_detector import Ocean_Optics_UV_vis
from custom_components.light_source.mirror_box_365nm.mirror_box_365nm import MirrorBox365nm


class DeviceExecutor:
    """Executes actions on various instrument types."""
    
    def __init__(self, bed_layouts, log_callback, start_time, continue_flag_getter):
        """
        Initialize the device executor.
        
        Args:
            bed_layouts: Dictionary of bed layouts {bed_number: BedLayout}
            log_callback: Function to call for logging (e.g., logger.log_to_csv)
            start_time: Experiment start time (datetime)
            continue_flag_getter: Function to check if experiment should continue
        """
        self.bed_layouts = bed_layouts
        self.log_to_csv = log_callback
        self.start_time = start_time
        self._continue_experiment_getter = continue_flag_getter
        self._pump_threads = []
    
    def execute_liquid_handler(self, action, params, component, liquid_handler: LiquidHandler):
        """Execute liquid handler actions using abstract interface methods."""
        if action == 'set_bedlayout':
            # TODO : Handle both GX281 and Ender3 bed layout settings to keep consistency
            bed, rack_layout = ParameterParser.extract_bed_rack_layout(params)
            # Check if liquid handler has set_bedlayout method (Ender3 does, GX281 may not)
            if hasattr(liquid_handler, 'set_bedlayout'):
                liquid_handler.set_bedlayout(bed, rack_layout)
            else:
                # Fallback to bed_layouts dict for GX281
                from liquid_handlers.bed_layout import BedLayout
                bed_layout = BedLayout(bed_number=bed, rack_layout=rack_layout)
                self.bed_layouts[bed] = bed_layout
                print(f"Bed {bed} layout set with rack_layout {rack_layout}")
            self.log_to_csv(component, action, params, f"Setting bed {bed} to bed layout {rack_layout}")

        elif action == 'move_home':
            liquid_handler.home()
            self.log_to_csv(component, action, "", "Homing liquid handler")

        elif action == 'move_z_height':
            z_coord = ParameterParser.extract_height(params)
            liquid_handler.move_z(z_coord)
            self.log_to_csv(component, action, params, f"Moving needle to z height {z_coord}")

        elif action == 'move_xy':
            bed, well = ParameterParser.extract_bed_well(params)

            # Move needle up to safe height before XY movement to avoid collisions
            safe_z = liquid_handler.get_safe_z_height()
            liquid_handler.move_z(safe_z)
            #This timer was added to ensure there is enough time to move the needle up
            time.sleep(1)
            self.log_to_csv(component, action, params,
                            f"Moving liquid handler needle up before moving xy coordinates: {safe_z}")
            
            # TODO : Really need to check consistency between GX281 and Ender3 here
            # Check if liquid handler has move_to_well (Ender3) or use coords (GX281)
            if hasattr(liquid_handler, 'move_to_well'):
                liquid_handler.move_to_well(bed, well)
            else:
                x = self.bed_layouts[bed].get_well(well).get_x()
                y = self.bed_layouts[bed].get_well(well).get_y()
                liquid_handler.move_xy(x, y)
            self.log_to_csv(component, action, params, f"Moving liquid handler to bed {bed} well {well}")

        elif action == 'move_z':
            bed, well = ParameterParser.extract_bed_well(params)

            # TODO : Really need to check consistency between GX281 and Ender3 here
            # Check if liquid handler has get_well_z (Ender3) or use bed_layouts
            if hasattr(liquid_handler, 'get_well_z'):
                z = liquid_handler.get_well_z(bed, well)
            else:
                z = self.bed_layouts[bed].get_well(well).get_z()
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
                volume_ml = ParameterParser.extract_syringe_volume(params)
                pump.select_syringe(volume_ml)
                self.log_to_csv(component, action, params, f"Selected syringe: {volume_ml} mL")
            except Exception as e:
                self.log_to_csv(component, action, params, f"Error selecting syringe: {e}")
            return

        # Extract parameters for aspirate/dispense
        flow_rate, volume = ParameterParser.extract_flow_rate_and_volume(params)

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
    
    def wait_for_pumps(self):
        """Block until every launched pump thread ends, then reset list."""
        for t in self._pump_threads:
            t.join()
        self.log_to_csv("SYNC", "wait_for_pumps", "", "All pumps finished")
        self._pump_threads.clear()  # ready for the next batch

    def execute_valve(self, action, params, component, valve: Valves):
        """Execute valve actions using abstract interface methods."""
        if action == 'go_to_position':
            position = ParameterParser.extract_position(params)
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

    def execute_temperature(self, action, params, component, temp_control: TemperatureController):
        """Execute temperature controller actions using abstract interface methods."""
        if action == 'set_temperature':
            temp = ParameterParser.extract_temperature_value(params)
            temp_control.set_temperature(temp)
            self.log_to_csv(component, action, params, f"Temperature controller set to {temp}°C")

        elif action == 'get_temperature':
            current_temp = temp_control.get_temperature()
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
                temp_control, target_temp, tolerance, duration, component
            )
            
            if converged:
                self.log_to_csv(component, action, params, 
                               f"Temperature converged to {target_temp}±{tolerance}°C")
            else:
                self.log_to_csv(component, action, params, 
                               f"Warning: Temperature convergence interrupted or failed")

        else:
            self.log_to_csv(component, action, params, f"Error: Unknown action '{action}' for temperature controller")

    def _wait_temperature_convergence(self, temp_control: TemperatureController, 
                                      target_temp: float, tolerance: float, 
                                      duration: float, component: str) -> bool:
        """
        Wait until temperature stays within tolerance range for specified duration.
        Checks every 5 seconds.
        Returns True if converged, False if interrupted.
        """
        from datetime import datetime
        check_interval = 5.0  # seconds between temperature checks
        stable_start_time = None
        
        while True:
            # Check if experiment should continue
            if not self._continue_experiment_getter():
                print(f"Temperature convergence wait interrupted by stop signal")
                return False
            
            try:
                current_temp = temp_control.get_temperature()
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
    
    def execute_dh2000(self, action, params, component, dh: DH2000LightSource):
        """
        DH2000 actions usable in the method CSV.
        Actions:
        shutter_open, shutter_close, halogen_toggle, deuterium_toggle,
        status, safe_shutdown
        """
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
                self.log_to_csv(component, action, params, str(st), notes="; ".join(st.get("arduino_output", [])))
            elif action == "safe_shutdown":
                dh.safe_shutdown()
                self.log_to_csv(component, action, params, "Shutdown ensured (Shutter CLOSED, Lamps OFF)")
            else:
                self.log_to_csv(component, action, params, f"Error: Unknown DH2000 action '{action}'")
                raise ValueError(f"Unknown DH2000 action '{action}'")
        except Exception as e:
            self.log_to_csv(component, action, params, f"Error: {e}")
            raise

    def execute_mirror_box(self, action, params, component, mirror_box: MirrorBox365nm):
        """
        MirrorBox365nm actions usable in the method CSV.
        Actions: set_dimmer, status, read_temperature
          set_dimmer  params: value=128   (0=brightest, 255=off)
        """
        try:
            if action == "set_dimmer":
                param_dict = {k.strip(): v.strip() for k, v in
                              (p.split('=') for p in params.split(','))}
                dimmer_value = int(param_dict.get('value', 255))
                response = mirror_box.set_dimmer(dimmer_value)
                self.log_to_csv(component, action, params, response or "OK")

            elif action == "status":
                st = mirror_box.status()
                notes = (f"L1={'ON' if st.get('light1_on') else 'OFF'} "
                         f"L2={'ON' if st.get('light2_on') else 'OFF'} "
                         f"TC3={st.get('temp_light1_c')}C "
                         f"TC4={st.get('temp_light2_c')}C")
                self.log_to_csv(component, action, params, str(st), notes=notes)

            elif action == "read_temperature":
                temp_data = mirror_box.read_temperature_stream()
                if 'error' in temp_data:
                    self.log_to_csv(component, action, params, f"Error: {temp_data['error']}")
                else:
                    notes = (f"TC3={temp_data.get('temp_light1_c')}C "
                             f"TC4={temp_data.get('temp_light2_c')}C")
                    self.log_to_csv(component, action, params, str(temp_data), notes=notes)

            else:
                self.log_to_csv(component, action, params,
                                f"Error: Unknown MirrorBox action '{action}'")
                raise ValueError(f"Unknown MirrorBox action '{action}'")

        except Exception as e:
            self.log_to_csv(component, action, params, f"Error: {e}")
            raise

    def execute_ocean_optics(self, action, params, component, uv: Ocean_Optics_UV_vis):
        """
        Actions:
        init
        record_blank
        record_dark
        load_blank_csv
        load_dark_csv
        measure_absorbance (records spectrum + calc absorbance + save plot)
        start_continuous
        stop_continuous
        set_params (integration_time=..., num_scans=..., measurement_interval=..., target_wavelengths=409;450)
        status
        """
        uv_detector_parameters = ParameterParser.extract_uv_detector_parameters(params)

        if action == "init":
            uv.connect()
            self.log_to_csv(component, action, params, "OK")

        elif action == "record_blank":
            uv.generate_and_record_blank_spectrum()
            uv.save_blank_spectrum(uv.output_dir)
            self.log_to_csv(component, action, params, "OK")

        elif action == "record_dark":
            uv.generate_and_record_dark_spectrum()
            uv.save_dark_spectrum(uv.output_dir)
            self.log_to_csv(component, action, params, "OK")

        elif action == "measure_absorbance":
            uv.recording_UV_VIS_Spectrum()
            uv.calculate_absorbance_spectrum()
            csv_path, png_path = uv.save_and_plot(Path(uv.output_dir))
            A = uv.get_absorbance_at_target_wavelengths()
            self.log_to_csv(component, action, params, f"A={A}", notes=f"{csv_path} ; {png_path}")

        elif action == "start_continuous":
            stop_upon = str(uv_detector_parameters.get("stop_upon_convergence", "False")).lower() == "true"
            name = uv_detector_parameters.get("name", None)
            uv.start_continuous(name=name, stop_upon_convergence=stop_upon)
            self.log_to_csv(component, action, params, "OK")

        elif action == "stop_continuous":
            uv.stop_continuous()
            self.log_to_csv(component, action, params, "OK")

        elif action == "set_params":
            if "integration_time" in uv_detector_parameters:
                uv.integration_time = int(uv_detector_parameters["integration_time"])
                if uv.initialized:
                    uv.set_integration_time()
            if "num_scans" in uv_detector_parameters:
                uv.set_number_of_scans(int(uv_detector_parameters["num_scans"]))
            if "measurement_interval" in uv_detector_parameters:
                uv.set_measurement_interval(uv_detector_parameters["measurement_interval"])
            if "target_wavelengths" in uv_detector_parameters:
                uv.set_target_wavelength(uv_detector_parameters["target_wavelengths"])
            self.log_to_csv(component, action, params, "OK")

        elif action == "status":
            st = uv.status()
            self.log_to_csv(component, action, params, str(st), notes="")

        else:
            self.log_to_csv(component, action, params, f"Error: unknown OceanOptics action '{action}'")
