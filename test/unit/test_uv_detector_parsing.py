# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Unit tests for UV detector — pure logic, no real serial hardware.
A MagicMock is attached directly to tc.ser; GeneralExperimentMethod is never involved.
"""

import pytest
from unittest.mock import patch

from uv_detectors.uv_detector.uv_detector import UVDetector
from conftest import make_uv_detector_response, make_uv_detector_device  

# ---------------------------------------------------------------------------
# Communication Connect and Close
# ---------------------------------------------------------------------------

class TestUVDetectorCommunication:

    def test_successful_initialization(self):
        """Test that the UV detector initializes successfully with a valid port."""
        with patch('serial.Serial') as mock_serial:
            mock_serial.return_value = make_uv_detector_device()
            uv_detector = UVDetector(port="COM_TEST")
            assert uv_detector.ser is not None
            print("Successful initialization test passed.")
        
    def test_failed_initialization(self):
        """Test that the UV handles failed initialization gracefully."""
        with patch('serial.Serial', side_effect=Exception("Serial connection failed")):
            uv_detector = UVDetector(port="COM_TEST")
            assert uv_detector.ser is None
            print("Failed initialization test passed.")

class TestUVDetectorParameters:

    def test_initialization(self):
        """Test that all parameters are initialized correctly."""
        uv_detector = UVDetector(port="COM_TEST")

        assert self.od == None
        assert self.device_id == None
        assert self.device == None
        assert self.initialized == False

        assert uv_detector.ser == None
        assert uv_detector.model == None

        #Spectrum Calibration
        assert uv_detector.blank_spectrum == None
        assert uv_detector.dark_spectrum == None
        assert uv_detector.raw_spectrum == None
        assert uv_detector.absorbance_spectrum == None

        assert uv_detector.spectra_sum == None
        assert uv_detector.wavelengths == None

        assert uv_detector.target_wavelengths == [float(409.0)]
        assert uv_detector.absorbance_at_target_wavelength == None

        # Thread control
        assert uv_detector._stop_flag == None
        assert uv_detector._worker_thread == None
        assert uv_detector._csv_file_path == None
        assert uv_detector._csv_writer == None
        assert uv_detector._start_time == None

        # Convergence monitoring
        assert uv_detector.convergence_enabled == False
        assert uv_detector.spike_level == 0.2
        assert uv_detector.convergence_threshold == 0.05
        assert uv_detector.convergence_time == 5 * 60  # 5 minutes in seconds
        assert uv_detector.max_outliers == 2  # Allow up to 2 outliers during convergence period
        assert uv_detector._convergence_state == {
            'previous': None,
            'spike_seen': False,
            'converged_start': None,
            'outliers': {},  # Dictionary: {outlier_number: timestamp}
            'done': False
        }

    def test_set_number_of_scans(self):
        uv_detector = UVDetector(port="COM_TEST")
        uv_detector.set_number_of_scans(10)
        assert uv_detector.number_of_scans == 10

    def test_set_number_of_scans_invalid(self):
        uv_detector = UVDetector(port="COM_TEST")
        with pytest.raises(ValueError, match="Number of scans must be a positive integer"):
            uv_detector.set_number_of_scans(-5)
    
    def test_set_target_wavelengths(self):
        uv_detector = UVDetector(port="COM_TEST")
        uv_detector.set_target_wavelengths([250.0, 300.0, 350.0])
        assert uv_detector.target_wavelengths == [250.0, 300.0, 350.0]

    def test_set_target_wavelengths_invalid(self):
        uv_detector = UVDetector(port="COM_TEST")
        with pytest.raises(ValueError, match="Target wavelengths must be a list of positive numbers"):
            uv_detector.set_target_wavelengths([-250.0, "300.0", "XYZ"])

    
    
