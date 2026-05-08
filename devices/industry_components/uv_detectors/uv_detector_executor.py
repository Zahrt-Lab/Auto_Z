# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Executor for Ocean Optics UV-Vis spectrometer actions.
Actions: init, record_blank, record_dark, load_blank_csv, load_dark_csv,
         measure_absorbance, start_continuous, stop_continuous, set_params, status.
"""

from pathlib import Path
from devices.industry_components.uv_detectors.uv_detector_base import UVDetector


class UvDetectorExecutor:
    """Executes CSV method actions for Ocean Optics UV-Vis spectrometer devices."""

    def __init__(self, log_callback):
        """
        Args:
            log_callback: Function to log an action row (component, action, params, output).
        """
        self.log_to_csv = log_callback

    def execute(self, action: str, params: str, component: str, uv: UVDetector):
        """Route action string to the appropriate UV detector method."""
        from methods.parameter_parser import parse_params
        uv_params = parse_params(params)

        if action == "init":
            uv.connect()
            self.log_to_csv(component, action, params, "OK")

        elif action == "record_blank":
            uv.generate_and_record_blank_spectrum(
                blank_light_intensity_threshold=uv.blank_light_intensity_threshold,
                wavelength_for_blank_light_intensity_check=uv.wavelength_for_blank_light_intensity_check,
            )
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
            self.log_to_csv(component, action, params, f"A={A}",
                            notes=f"{csv_path} ; {png_path}")

        elif action == "start_continuous":
            stop_upon = str(uv_params.get("stop_upon_convergence", "False")).lower() == "true"
            name = uv_params.get("name", None)
            uv.start_continuous(filename=name, stop_upon_convergence=stop_upon)
            self.log_to_csv(component, action, params, "OK")

        elif action == "stop_continuous":
            uv.stop_continuous()
            self.log_to_csv(component, action, params, "OK")

        elif action == "load_blank_csv":
            path = uv_params.get("path", "")
            uv.load_blank_spectrum_from_csv(path)
            self.log_to_csv(component, action, params, "OK")

        elif action == "load_dark_csv":
            path = uv_params.get("path", "")
            apply = str(uv_params.get("apply_to_device", "True")).lower() == "true"
            uv.load_dark_spectrum_from_csv(path, apply_to_device=apply)
            self.log_to_csv(component, action, params, "OK")

        elif action == "set_params":
            if "integration_time" in uv_params:
                uv.integration_time = int(uv_params["integration_time"])
                if uv.initialized:
                    uv.set_integration_time()
            if "num_scans" in uv_params:
                uv.set_number_of_scans(int(uv_params["num_scans"]))
            if "measurement_interval" in uv_params:
                uv.set_measurement_interval(uv_params["measurement_interval"])
            if "target_wavelengths" in uv_params:
                uv.set_target_wavelength(uv_params["target_wavelengths"])
            if "convergence_enabled" in uv_params:
                uv.convergence_enabled = str(uv_params["convergence_enabled"]).lower() == "true"
            if "spike_level" in uv_params:
                uv.spike_level = float(uv_params["spike_level"])
            if "convergence_threshold" in uv_params:
                uv.convergence_threshold = float(uv_params["convergence_threshold"])
            if "convergence_time" in uv_params:
                uv.convergence_time = float(uv_params["convergence_time"])
            if "max_outliers" in uv_params:
                uv.max_outliers = int(uv_params["max_outliers"])
            if "max_convergence_wait" in uv_params:
                uv.max_convergence_wait = float(uv_params["max_convergence_wait"])
            if "reference_wavelength" in uv_params:
                uv.set_reference_wavelength(uv_params["reference_wavelength"])
            if "blank_light_intensity_threshold" in uv_params:
                uv.blank_light_intensity_threshold = float(uv_params["blank_light_intensity_threshold"])
            if "wavelength_for_blank_light_intensity_check" in uv_params:
                uv.wavelength_for_blank_light_intensity_check = float(uv_params["wavelength_for_blank_light_intensity_check"])
            self.log_to_csv(component, action, params, "OK")

        elif action == "status":
            st = uv.status()
            self.log_to_csv(component, action, params, str(st), notes="")

        else:
            self.log_to_csv(component, action, params,
                            f"Error: Unknown OceanOptics action '{action}'")
