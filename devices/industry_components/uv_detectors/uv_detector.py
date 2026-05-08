# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

import os
import pandas as pd
from pathlib import Path
import sys
import csv
import numpy as np
from datetime import datetime
import threading
import time
from typing import List, Optional


# set headless backend before pyplot
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

#from safetensors.flax import save_file
# Need to include the OceanDirect SDK path dynamically in the future when uploading to different computers

# Is this a 64-bit Python process?
is_py64 = sys.maxsize > 2**32

# Candidate SDK paths (64-bit first if Python is 64-bit, else 32-bit first)
# TODO : Need to update this to be more dynamic in the future for different computers
candidates = [
    Path(r"C:\Program Files\Ocean Optics\OceanDirect SDK\Python"),
    Path(r"C:\Program Files (x86)\Ocean Optics\OceanDirect SDK\Python"),
]
if not is_py64:
    candidates.reverse()

# TODO : Need to make Ocean Optics SDK more dynamic in the future for different computers, should include it in the UV detector scripts
'''
'''
#####################################################################################################################################
# Try to import OceanDirect SDK - make it optional
OceanDirectAPI = None
OceanDirectError = None
try:
    for p in candidates:
        if p.exists():
            sys.path.append(str(p))
            from oceandirect.OceanDirectAPI import OceanDirectAPI as _OceanDirectAPI
            from oceandirect.OceanDirectAPI import OceanDirectError as _OceanDirectError
            OceanDirectAPI = _OceanDirectAPI
            OceanDirectError = _OceanDirectError
            break
    else:
        # SDK not found - this is okay for systems without Ocean Optics hardware
        print("Warning: OceanDirect SDK not found. Ocean Optics UV-Vis functionality will be limited.")
except ImportError as e:
    print(f"Warning: Could not import OceanDirect SDK: {e}. Ocean Optics UV-Vis functionality will be limited.")
####################################################################################################################################
#Object for Ocean Optics to connect to the rest of the platform
from devices.industry_components.uv_detectors.uv_detector_base import UVDetector


class Ocean_Optics_UV_vis(UVDetector):

    #Initiates the platform
    def __init__(self, output_dir, baseline_intensity = 10000, integration_time = 100000, num_scans = 10, target_wavelengths = None, reference_wavelength = 700, blank_light_intensity_threshold=500, wavelength_for_blank_light_intensity_check=400, save_file_path="UV_detection.csv", measurement_interval =20.0):

        '''
        Device used to communicate with the Ocean Optics HR2000 device, using the following code to communicate
        Reference: (https://www.oceanoptics.com/software/oceandirect/)
        where to output the results:param output_dir:
        Measures the baseline intensity of device measured:param baseline_intensity:
        Set integration_time of the device to use:param integration_time:
        Number of Scans it needs to perform to average:param num_scans:
        Wavelength to record during all the scans:param target_wavelength:
        Reference wavelength for absorbance calculation:param reference_wavelength:
        Which file path to save it all to:param save_file_path:
        Light intensity threshold for detection:param light_intensity_threshold:
        Wavelength for light intensity check:param wavelength_for_light_intensity_check:
        '''
        # Check if SDK is available
        if OceanDirectAPI is None:
            raise RuntimeError("OceanDirect SDK is not available. Cannot initialize Ocean_Optics_UV_vis.")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.integration_time = int(integration_time)
        if self.integration_time <= 0:
            raise ValueError("integration_time must be positive")
        self.num_scans = int(num_scans)
        if self.num_scans <= 0:
            raise ValueError("num_scans must be positive")
        self.measurement_interval = float(measurement_interval)
        if self.measurement_interval <= 0:
            raise ValueError("measurement_interval must be positive")

        # The base_line intensity loads a csv file containing the Intensity at the beginning, should be done shortly before experiment begins
        self.baseline_intensity = float(baseline_intensity)
        #User will need to set where to save the file to w
        self.save_file_path = Path(output_dir) / save_file_path

        self.od = None
        self.device_ids = None
        self.device = None
        self.initialized = False


        self.serial = None
        self.model = None

        #Spectrum Calibration
        self.blank_spectrum = None
        self.dark_spectrum = None
        self.raw_spectrum = None
        self.absorbance_spectrum = None

        self.spectra_sum = None
        self.wavelengths = None

        if target_wavelengths is None:
            self.target_wavelengths = [409.0]
        else:
            self.target_wavelengths = [float(wl) for wl in target_wavelengths]

        if reference_wavelength is None:
            self.reference_wavelength = 700.0
        else:
            self.reference_wavelength = float(reference_wavelength)

        self.absorbance_at_target_wavelengths = None

        self.blank_light_intensity_threshold = blank_light_intensity_threshold
        self.wavelength_for_blank_light_intensity_check = wavelength_for_blank_light_intensity_check

        # Thread control
        self._stop_flag: Optional[threading.Event] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._csv_file_path = None
        self._csv_writer = None
        self._start_time: Optional[datetime] = None
        
        # Convergence monitoring
        self.convergence_enabled = False
        self.spike_level = 0.2
        self.convergence_threshold = 0.05
        self.convergence_time = 3 * 60  # 3 minutes in seconds
        self.max_outliers = 2  # Allow up to 2 outliers during convergence period
        self.max_convergence_wait = None  # Optional timeout in seconds (None = no limit)
        self.instrument_control_file = None  # Injected by GeneralExperimentMethod
        self.convergence_stop_callback = None  # Injected by GeneralExperimentMethod
        self._convergence_state = {
            'previous': None,
            'spike_seen': False,
            'converged_start': None,
            'outliers': [],  # List of timestamps for outlier points
            'done': False
        }

    """
    Measures the UV-VIS spectrum and returns the intensity at a specific wavelength.
    Optionally computes absorbance if a baseline (I0) is provided, records individual scans,
    and saves the averaged spectrum to a CSV file.

    Parameters:
        The target wavelengths float): The wavelengths (nm) at which to evaluate the measurement.
        num_scans (int): Number of scans to average.
        integration_time (int): Integration time in microseconds.
        save_file_path (str, optional): If provided, saves the averaged spectrum to the given CSV file path.

    Returns:
        dict: A dictionary with keys:
              - "target_wavelength": the wavelength provided,
              - "measured_intensity": the averaged intensity at the target wavelength,
              - "absorbance": computed absorbance (or None if baseline_intensity is not provided),
              - "wavelengths": the list/array of wavelengths,
              - "averaged_spectrum": the averaged intensity spectrum,

    """

    def connect(self):
        self.initialize_Ocean_Optics_UV_VIS()
        self.retrieve_Ocean_Optics_Model()
        # Apply configured acquisition settings
        self.set_number_of_scans(self.num_scans)
        self.set_integration_time()

    def status(self):
        return {
            "initialized": self.initialized,
            "model": self.model,
            "serial": self.serial,
            "integration_time_us": self.integration_time,
            "num_scans": self.num_scans,
            "targets_nm": self.target_wavelengths,
            "interval_s": self.measurement_interval,
        }

    # Initialize and open the device
    def initialize_Ocean_Optics_UV_VIS(self):
        # Creates the instance of our ocean optics instance object
        od = OceanDirectAPI()
        # This finds al the USB devices if any, if 0, no UV-VIS spectrometers were found
        if od.find_usb_devices() == 0:
            raise RuntimeError("No spectrometer devices found")

        # This sets the instances as an attribute of our Ocean_Optics_UV_vis class
        self.od = od
        # Specifies the Device ID object in our Ocean_Optics_UV_vis class
        # If just one spectrometer it should be set to 2
        self.device_ids = od.get_device_ids()
        # Opens the device which allows operations to be performed on the spectrometer such as gathering the UV data
        self.device = od.open_device(self.device_ids[0])

        actual = self.device.get_scans_to_average()
        print(f"Hardware default scans-to-average: {actual}")
        self.initialized = True

    #Obtains all the information about the device
    def retrieve_Ocean_Optics_Model(self):
        try:
            self.serial = self.device.get_serial_number()
            self.model = self.device.get_model()
            print(f"Device Serial Number: {self.serial}")
            print(f"Device Model: {self.model}")
        except OceanDirectError as e:
            print("Error retrieving device information:", e.get_error_details())
            return None

    # Set the integration time of the device
    def set_integration_time(self):
        self.ensure_init()
        if self.integration_time < 0:
            print("Integration Time must be a positive value (ex. 50000 is 50ms")
        try:
            self.device.set_integration_time(self.integration_time)
            print(f"Integration time set to {self.integration_time} µs.")
        except OceanDirectError as e:
            print("Integration time error:", e.get_error_details())
            return None

    #Sets the number of scans for this device
    def set_number_of_scans(self, num_scans):
        try:
            self.num_scans = num_scans
            print(f"Set number of scans to {self.num_scans}")
            if self.initialized:
                self.device.set_scans_to_average(self.num_scans)
        except:
            print(f"Failed to set number of scans to {num_scans}")

    #Sets the target wavelength of the device to be recorded in the form of a list
    def set_target_wavelength(self, target_wavelengths):
        #This input is a list of target wavelengths that we wish to record to track the progress of the reaction
        try:
            if isinstance(target_wavelengths, str):
                target_wavelengths_normalized = target_wavelengths.replace(",", ";")
                wls = [wl.strip() for wl in target_wavelengths_normalized.split(";") if wl.strip()]
                self.target_wavelengths = [float(wl) for wl in wls]
            # TODO : Should change this to a log message in the future
            print(f"Set target wavelengths to {self.target_wavelengths}")
        except:
            print(f"FAILED TO SET TARGET WAVELENGTHS TO {target_wavelengths}")

    def set_reference_wavelength(self, reference_wavelength):
        '''This sets the reference wavelength for the absorbance calculations'''
        try:
            self.reference_wavelength = float(reference_wavelength)
            print(f"Set reference wavelength to {self.reference_wavelength} nm")
        except:
            print(f"FAILED TO SET TARGET REFERENCE WAVELENGTH TO {reference_wavelength}")


    #This sets how frequently things are being recorded on the device
    def set_measurement_interval(self, measurement_interval):
        try:
            self.measurement_interval =float(measurement_interval)
            print(f"Set measurement interval to {self.measurement_interval}")
        except:
            print(f"Failed to set measurement interval to {measurement_interval}")

    # Returns output directory of where to save everything
    def get_output_directory(self):
        return self.output_dir

    # This records the UV-VIS Spectrum at a particular time point
    def recording_UV_VIS_Spectrum(self):
        self.ensure_init()

        # Sets the number of scan to perform on average when recording intensity of the plot
        self.device.set_scans_to_average(self.num_scans)

        # Sets the integration time for this device
        self.device.set_integration_time(self.integration_time)

        try:

            #This function returns a one-dimensional array of pixel values, stored as doubles.
            self.raw_spectrum = np.array(self.device.get_formatted_spectrum())

            self.wavelengths = np.array(self.device.get_wavelengths())
            print("Spectra averaged successfully.")

        #Something went wrong when performing this scan
        except OceanDirectError as e:
            print("Error acquiring spectrum or wavelengths:", e.get_error_details())
            return None

    #This will be used to generate and record our dark spectrum for this project
    def generate_and_record_dark_spectrum(self, attempts=3, delay_between_attempts=5):

        for _ in range(attempts):
            self.ensure_init()
            self.device.set_scans_to_average(self.num_scans)
            self.device.set_integration_time(self.integration_time)
            self.device.set_electric_dark_correction_usage(True)
            #store as your IO spectrum
            self.dark_spectrum = self.device.get_formatted_spectrum()
            self.device.set_stored_dark_spectrum(self.dark_spectrum)
            self.dark_spectrum = np.array(self.dark_spectrum)
            # also wavelengths
            self.wavelengths = np.array(self.device.get_wavelengths())
            if self.wavelength_for_blank_light_intensity_check is not None and self.blank_light_intensity_threshold is not None:
                intensity_at_check_wavelength = np.interp(self.wavelength_for_blank_light_intensity_check, self.wavelengths, self.dark_spectrum)
                if intensity_at_check_wavelength > self.blank_light_intensity_threshold:
                    print(f"WARNING: INTENSITY AT {self.wavelength_for_blank_light_intensity_check} nm IS {intensity_at_check_wavelength},"
                          f" WHICH IS ABOVE THE TARGET THRESHOLD: {self.blank_light_intensity_threshold}.")
                else:
                    print("Dark Spectrum Recorded Successfully")
                    break
            time.sleep(delay_between_attempts)
        else:
            print(f"WAS UNABLE TO RECORD A DARK SPECTRUM BELOW THE THRESHOLD OF {self.blank_light_intensity_threshold} AFTER MULTIPLE ATTEMPTS")
            print("STOPPING ALL UV-VIS MEASUREMENTS AND EXPERIMENTS")
            raise RuntimeError("Failed to record valid dark spectrum")
    

    #This will set nonlinearity corrections within the spectrum to be True
    #Default is True
    def set_nonlinearity_correction(self):
        self.device.set_nonlinearity_correction_usage(True)

    #This will measure the absorbance of our blank with solvent but no product
    def generate_and_record_blank_spectrum(self, blank_light_intensity_threshold, wavelength_for_blank_light_intensity_check, attempts=3, delay_between_attempts=5):
        """Measure the solvent (blank) to use as I0 for absorbance."""

        for _ in range(attempts):
            # measure blank (solvent only)
            self.ensure_init()
            self.device.set_scans_to_average(self.num_scans)
            self.device.set_integration_time(self.integration_time)
            # store as your I0 spectrum
            self.blank_spectrum = np.array(self.device.get_formatted_spectrum())
            # also wavelengths
            self.wavelengths = np.array(self.device.get_wavelengths())
            intensity_at_check_wavelength = np.interp(wavelength_for_blank_light_intensity_check, self.wavelengths, self.blank_spectrum)
            if intensity_at_check_wavelength < blank_light_intensity_threshold:
                print(f"WARNING: INTENSITY AT {wavelength_for_blank_light_intensity_check} nm IS {intensity_at_check_wavelength},"
                      f" WHICH IS BELOW THE TARGET THRESHOLD: {blank_light_intensity_threshold}.")
            else:
                print("Blank Spectrum Recorded Successfully")
                break
            time.sleep(delay_between_attempts)
        else:
            print(f"WAS UNABLE TO RECORD A BLANK SPECTRUM ABOVE THE THRESHOLD OF {blank_light_intensity_threshold}"
                  f" at wavelength {wavelength_for_blank_light_intensity_check} AFTER MULTIPLE ATTEMPTS")
            print("STOPPING ALL UV-VIS MEASUREMENTS AND EXPERIMENTS")
            raise RuntimeError("Failed to record valid blank spectrum")

    # This records the dark spectrum as a csv file within a specific directory
    def save_dark_spectrum(self, output_dir, filename=None):
        """
        Save the last-measured dark spectrum to CSV and PNG.
        Requires: self.dark_spectrum and self.wavelengths.
        """
        if self.dark_spectrum is None or self.wavelengths is None:
            raise RuntimeError("No dark spectrum available; run generate_and_record_dark_spectrum() first")

        outdir = Path(output_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        base = filename or "dark_spectrum"
        csv_path = outdir / f"{base}.csv"
        png_path = outdir / f"{base}.png"

        # CSV
        with open(csv_path, "w", newline="") as fp:
            w = csv.writer(fp)
            w.writerow(["Wavelength (nm)", "Intensity (raw dark)"])
            for wl, inten in zip(self.wavelengths, self.dark_spectrum):
                w.writerow([wl, inten])
        print(f"Dark spectrum CSV saved to {csv_path}")

        # PNG
        plt.figure()
        plt.plot(self.wavelengths, self.dark_spectrum, label="Dark")
        plt.xlabel("Wavelength (nm)")
        plt.ylabel("Intensity")
        plt.title("Dark Spectrum")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(png_path, dpi=600)
        plt.close()
        print(f"Dark spectrum plot saved to {png_path}")

    # Saves the blank spectrum to a CSV and a PNG file
    def save_blank_spectrum(self, output_dir, filename=None):
        """
        Save the last-measured blank (solvent) spectrum to CSV and PNG.
        Requires: self.blank_spectrum and self.wavelengths.
        """
        if self.blank_spectrum is None or self.wavelengths is None:
            raise RuntimeError("No blank spectrum available; run generate_and_record_blank_spectrum() first")

        outdir = Path(output_dir)
        outdir.mkdir(parents=True, exist_ok=True)
        base = filename or "blank_spectrum"
        csv_path = outdir / f"{base}.csv"
        png_path = outdir / f"{base}.png"

        with open(csv_path, "w", newline="") as fp:
            w = csv.writer(fp)
            w.writerow(["Wavelength (nm)", "Intensity (raw blank)"])
            for wl, inten in zip(self.wavelengths, self.blank_spectrum):
                w.writerow([wl, inten])
        print(f"Blank spectrum CSV saved to {csv_path}")

        plt.figure()
        plt.plot(self.wavelengths, self.blank_spectrum, label="Blank (solvent)")
        plt.xlabel("Wavelength (nm)")
        plt.ylabel("Intensity")
        plt.title("Blank Spectrum")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(png_path, dpi=600)
        plt.close()
        print(f"Blank spectrum plot saved to {png_path}")

    # Loads dark_spectrum and if applicable load to the UV-Spectrum to the device
    def load_dark_spectrum_from_csv(self, path, apply_to_device=True):
        """
        Load dark spectrum from a 2-column CSV with header:
            Wavelength (nm),Intensity (raw dark)
        Sets self.wavelengths and self.dark_spectrum.
        If apply_to_device=True and device is initialized, calls set_stored_dark_spectrum().
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Dark spectrum CSV not found: {path}")

        wavelength, intensity = [], []
        with open(path, "r", newline="") as filepath:
            dark_spectrum_csv_file = csv.reader(filepath)

            #This skips the header since it's not relevant to our data processing
            header = next(dark_spectrum_csv_file, None)  # skip header
            for row in dark_spectrum_csv_file:
                if not row:
                    continue
                wavelength.append(float(row[0]))
                intensity.append(float(row[1]))

        wavelength = np.array(wavelength, dtype=float)
        intensity = np.array(intensity, dtype=float)

        self.wavelengths = wavelength
        self.dark_spectrum = intensity
        print(f"Loaded dark spectrum from {path}")

        if apply_to_device:
            try:
                self.ensure_init()
                self.device.set_stored_dark_spectrum(self.dark_spectrum.tolist())
                self.device.set_electric_dark_correction_usage(True)
                print("Applied dark spectrum to device")
            except Exception:
                print("Loaded dark spectrum but could not apply to device")

    # Loads the blank spectrum to the csv file
    def load_blank_spectrum_from_csv(self, path):
        """
        Load blank spectrum from a 2-column CSV with header:
            Wavelength (nm),Intensity (raw blank)
        Sets self.wavelengths and self.blank_spectrum.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Blank spectrum CSV not found: {path}")

        wavelength, intensity = [], []
        with open(path, "r", newline="") as file_path:
            blank_spectrum_csv_file = csv.reader(file_path)
            header = next(blank_spectrum_csv_file, None)  # skip header
            for row in blank_spectrum_csv_file:
                if not row:
                    continue
                wavelength.append(float(row[0]))
                intensity.append(float(row[1]))

        wavelength = np.array(wavelength, dtype=float)
        intensity = np.array(intensity, dtype=float)

        self.wavelengths = wavelength
        self.blank_spectrum = intensity
        print(f"Loaded blank spectrum from {path}")

    # Calculates the absorbance spectrum of our plot given the intensity
    def calculate_absorbance_spectrum(self):

        # This indicates no blank spectrum or raw spectrum file is provided
        if self.blank_spectrum is None or self.raw_spectrum is None:
            raise RuntimeError("Need blank and sample spectra first")

        #The purpose of this epsilon is to set the lowest value to 1e-12 so there are no divide by zero errors
        eps = 1e-12
        self.blank_spectrum = np.maximum(self.blank_spectrum, eps)
        self.raw_spectrum = np.maximum(self.raw_spectrum, eps)

        """Compute A = -log10[(I_sample - dark) / (I_blank - dark)]."""
        # blank_spectrum already includes dark subtraction and not included in the calculations
        self.absorbance_spectrum = -np.log10(self.raw_spectrum / self.blank_spectrum)

    #Closes the UV-VIS spectrometer
    def close_device(self):
        try:
            self.device.close_device()
            self.initialized = False
            print("Device closed successfully.")
        except:
            print("Unable to close Ocean Optics UV-VIS spectrometer")

    #Saves the absorbance spectrum
    def save_and_plot(self, output_dir, base_name=None):
        """
        Save the current absorbance spectrum to CSV and PNG inside `output_dir`.
        If `base_name` is None, a timestamp will be used.
        Returns (csv_path, png_path).
        """

        self.ensure_init()
        if self.absorbance_spectrum is None:
            raise RuntimeError("No absorbance data – run calculate_absorbance_spectrum() first")

        # Saves and plots the UV absorbance measured at a particular point in time with csv and png file
        base = base_name or f"absorbance_{datetime.now():%Y%m%d_%H%M%S}"
        csv_path = output_dir / f"{base}.csv"
        png_path = output_dir / f"{base}.png"

        np.savetxt(csv_path, np.column_stack((self.wavelengths, self.absorbance_spectrum)),
                   delimiter=",", header="Wavelength (nm),Absorbance", comments="")

        # Saves the PNG at a particular timepoint during the Bayesian Optimization
        plt.figure()
        plt.plot(self.wavelengths, self.absorbance_spectrum)
        plt.xlabel("Wavelength (nm)")
        plt.ylabel("Absorbance")
        plt.title(f"Absorbance (target {self.target_wavelengths} nm)")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(png_path, dpi=600)
        plt.close()

        return csv_path, png_path

    # This function selects a series of wavelengths and records the absorption of these wavelengths over time
    def get_absorbance_at_target_wavelengths(self) -> list[float]:
        """
        Return the absorbance at self.target_wavelengths (nm), using linear
        interpolation if the exact wavelength isn’t in self.wavelengths.
        """

        if self.absorbance_spectrum is None or self.wavelengths is None:
            raise RuntimeError(
                "No absorbance spectrum available; run calculate_absorbance_spectrum() first"
            )

        # numpy.interp will linearly interpolate (and clamp at ends) for you
        self.absorbance_at_target_wavelengths = np.interp(self.target_wavelengths, self.wavelengths, self.absorbance_spectrum) \
                                              - np.interp(self.reference_wavelength, self.wavelengths, self.absorbance_spectrum) 
                
        return self.absorbance_at_target_wavelengths.tolist()
    
    def start_continuous(self, filename=None, stop_upon_convergence=False):
        """
        Start background thread to log absorbance at all target wavelengths. 
        While pump are running in flow in the background.
        
        Parameters:
        - filename: Optional name for output files (without extension)
        - stop_upon_convergence: If True, checks for convergence and stops monitoring when met
        """

        # The purpose of this is to check if there is a UV monitoring thread already running,
        # it will prevent it from starting a second thread. 
        if self._worker_thread and self._worker_thread.is_alive():
            print("Continuous monitoring already running")
            return

        # This represents the stop condition for the thread, this will be set to False 
        # until the stop condition is met, then it will be set to True, signaling the thread to stop
        self._stop_flag = threading.Event()
        self._stop_upon_convergence = stop_upon_convergence
        if stop_upon_convergence:
            self.convergence_enabled = True

        # This is creates the CSV file and writes the header with the target wavelengths as columns
        self._continuous_uv_measurement_csv = open(self.save_file_path, "w", newline="")
        #This creates the csv writer object that appends all the data to the csv file
        self._csv_writer = csv.writer(self._continuous_uv_measurement_csv)
        # Creaters header to record 
        header = ["Time(s)"] + [str(wl) for wl in self.target_wavelengths]
        self._csv_writer.writerow(header)

        # This is the start time for the uv experiment
        self._start_time = datetime.now()

        def _worker():
            """
            This is the worker function to continously record UV detector in the background
            """
            try:
                # As long as the stop condition is not met, this thread will keep running
                while not self._stop_flag.is_set():
                    self.recording_UV_VIS_Spectrum()
                    self.calculate_absorbance_spectrum()
                    # Is the absorbance at the target wavelengths, as a numpy array of float values
                    absorbance = self.get_absorbance_at_target_wavelengths()
                    # Captures the total time that has passed since the start of the uv-vis experiment
                    elapsed_time = (datetime.now() - self._start_time).total_seconds()
                    # Writes the elapsed time and the absorbance at the target wavelengths to the csv file
                    self._csv_writer.writerow([elapsed_time] + absorbance)
                    # Ensures the uv-vis data is written to the csv file
                    self._csv_writer.flush()

                    if self._stop_upon_convergence:
                        if self.max_convergence_wait is not None and time.time() - self._start_time.timestamp() > self.max_convergence_wait:
                            print("UV convergence timed out — stopping monitoring")
                            break
                        # Checks if convergence criteria are met, True if met, False if not met
                        if self.check_convergence_from_csv():
                            # What is the purpose if this convergence stop callback function? 
                            if self.convergence_stop_callback:
                                self.convergence_stop_callback()
                            self._update_control_file()
                            break
                    
                    time.sleep(self.measurement_interval)
            
            except Exception:
                
                print("Error in continuous monitoring worker")

            finally:
                try:
                    self._continuous_uv_measurement_csv.close()
                except Exception:
                    pass
                self._dump_final_plot(filename)
        
        self._worker_thread = threading.Thread(target=_worker, daemon=True)
        self._worker_thread.start()
        print("Continuous monitoring started")

    def stop_continuous(self):
        """
        Signal the monitoring thread to stop and wait for it to finish.
        """
        if not self._stop_flag:
            print("No continuous monitoring to stop")
            return
        self._stop_flag.set()
        self._worker_thread.join(timeout=5)
        print("Continuous monitoring stopped")

    def _dump_final_plot(self, name = None):
        """
        Read the CSV and save a final multi-wavelength timecourse plot.
        """
        try:
            import pandas as pd
            df = pd.read_csv(self.save_file_path)
            plt.figure()
            for wl in self.target_wavelengths:
                plt.plot(df["Time(s)"], df[str(wl)], label=f"{wl} nm")
            plt.xlabel("Time (s)")
            plt.ylabel("Absorbance")
            plt.legend()
            plt.tight_layout()
            suffix = f"_{name}" if name else ""
            png = self.output_dir / f"UV_VIS_timecourse{suffix}.png"
            pdf = self.output_dir / f"UV_VIS_timecourse{suffix}.pdf"
            plt.savefig(png, dpi=600)
            plt.savefig(pdf)
            plt.close()
            print(f"Final plots saved to {png} and {pdf}")
        except Exception:
            print("Failed to generate final plot")

    def ensure_init(self):
        if not self.initialized:
            raise RuntimeError(
                "Spectrometer not initialized — call `initialize_Ocean_Optics_UV_VIS()` first"
            )
    
    def _update_control_file(self):
        """Write False to instrument_control.txt to stop the experiment on convergence."""
        try:
            if not self.instrument_control_file:
                return
            control_file = Path(self.instrument_control_file)
            if control_file.exists():
                content = control_file.read_text().strip()
                if content == "True":
                    control_file.write_text("False")
                    print(f"Updated {control_file}: True -> False (convergence met)")
        except Exception as e:
            print(f"Warning: Could not update control file: {e}")

    def check_convergence_from_csv(self):
        """
        Reads a csv file and checks if the UV-VIS measurements have converged based on two criteria:
                1. Spike detection: once one of the measured wavelengths are greater than or equal to the spike threshold,
                   the converge monitoring will be initiated.
                2. Convergence, the signal is stable for a set period of time 
        """       
        try:
            # Loads the csv file containing the UV-VIS measurements, 
            continous_absorbance_df = pd.read_csv(self.save_file_path)

            # If the file is empty, with no rows it returns False
            if len(continous_absorbance_df) < 1:
                return False
            
            # This gets the absorbance values for each target wavelength at the last scanned timepoint
            # Column 0 is time, so only columns from 1 onwards are the target wavelengths
            current_absorbance_values_each_wavelength = continous_absorbance_df.iloc[-1, 1:].values

            # If there are no previous values, it will store the current values as the previous values
            # It returns False because there is no basis for comparison yet
            if self._convergence_state['previous'] is None:
                self._convergence_state['previous'] = current_absorbance_values_each_wavelength
                return False
            
            # 1) Wait for spike, if spike occurs that start experiment convergence monitoring
            if not self._convergence_state['spike_seen']:
                # If any of the current absorbance values at the target wavelengths are greater than
                # or equal to the spike level, it will set the spike seen flag to True and reset the
                # converged start time to None to start fresh for convergence monitoring
                if any(current_absorbance_values_each_wavelength) >= self.spike_level:
                    self._convergence_state['spike_seen'] = True
                    self._convergence_state['converged_start'] = None
                # It will update the previous value to the current value and return False to continue monitoring for convergence
                self._convergence_state['previous'] = current_absorbance_values_each_wavelength
                return False
            
            # 2) After spike, is detected convergence is checked every timepoint

            # This calculates the absolute difference between the current absorbance values and the previous absorbance values 
            # for each target wavelength
            absorbance_differences = [abs(current - previous) for current, previous in zip(current_absorbance_values_each_wavelength, self._convergence_state['previous'])]

            current_time = time.time()
            # If the monitoring til convergence has already started
            # It will delete any outliers that are outside the convergence time window
            if self._convergence_state['converged_start'] is not None:
                window_start = current_time - self.convergence_time
                self._convergence_state['outliers'] = \
                                  [timestamp for timestamp in self._convergence_state['outliers'] if timestamp >= window_start]
            
            # Checks if the maximum difference across all target wavelengths is less than the convergence threshold
            if max(absorbance_differences) < self.convergence_threshold:

                if self._convergence_state['converged_start'] is None:
                    # Sets convergence start time to the current time
                    self._convergence_state['converged_start'] = current_time
                    # Resets the outliers list when starting convergence monitoring
                    self._convergence_state['outliers'] = []  

                else:
                    # Checks time elapsed since convergence monitoring started
                    time_elapsed = current_time - self._convergence_state['converged_start']
                    # Checks if the time elapsed is greater than or equal to the required convergence time
                    if time_elapsed >= self.convergence_time:
                        # Checks if the number of outliers within the convergence window is less than or equal to the maximum allowed outliers
                        if len(self._convergence_state['outliers']) <= self.max_outliers:
                            if not self._convergence_state['done']:
                                self._convergence_state['done'] = True
                                print(f"UV convergence criteria met (with {len(self._convergence_state['outliers'])} outliers) - stopping monitoring")
                                return True
            
            # If the maximum difference exceeds the convergence threshold
            else:
                # If convergence monitoring is in progress, it will record this timepoint as an outlier
                if self._convergence_state['converged_start'] is not None:
                    #This adds the current time to the list of outliers
                    self._convergence_state['outliers'].append(current_time)

                    # If the number of outliers is greater than the maximum allowed outliers
                    if len(self._convergence_state['outliers']) > self.max_outliers:
                        # It will reset the convergence monitoring by setting the convergence start time to None and clearing the outliers list
                        print(f"Convergence reset: too many outliers ({len(self._convergence_state['outliers'])}) within {self.convergence_time}s window")
                        self._convergence_state['converged_start'] = None
                        self._convergence_state['outliers'] = []
                    
            self._convergence_state['previous'] = current_absorbance_values_each_wavelength
            return False

        except Exception as e:
            print(f"Error reading CSV for convergence check: {e}")
            return False
        
    def close(self):
        self.close_device()

    def safe_shutdown(self, success: bool) -> None:
        pass


'''
od = OceanDirectAPI()
print("OceanDirect API version:", od.get_api_version_numbers())
od.find_usb_devices()
dev = od.open_device(od.get_device_ids()[0])
print("Model:", dev.get_model())
print("Serial:", dev.get_serial_number())
print("Pixels:", dev.get_formatted_spectrum_length())
'''