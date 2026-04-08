# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Unit tests for Ocean_Optics_UV_vis — pure logic, no real hardware or SDK.
OceanDirectAPI is mocked at the module level so no Ocean Optics SDK is required.
"""

import tempfile
import pytest
from unittest.mock import MagicMock, patch

from devices.industry_components.uv_detectors.uv_detector import Ocean_Optics_UV_vis

# Patch target that makes the SDK appear available
_OCEAN_API_PATH = "devices.industry_components.uv_detectors.uv_detector.OceanDirectAPI"


def _make_device(**kwargs) -> Ocean_Optics_UV_vis:
    """Return an Ocean_Optics_UV_vis with a mocked SDK and a real temp directory."""
    output_dir = tempfile.mkdtemp()
    with patch(_OCEAN_API_PATH, MagicMock()):
        uv = Ocean_Optics_UV_vis(output_dir=output_dir, **kwargs)
    return uv


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestOceanOpticsInitialization:

    def test_sdk_not_available_raises(self):
        """RuntimeError is raised when the OceanDirect SDK is unavailable."""
        with patch(_OCEAN_API_PATH, None):
            with pytest.raises(RuntimeError):
                Ocean_Optics_UV_vis(output_dir=tempfile.mkdtemp())

    def test_default_attributes(self):
        """All attributes are initialized to their expected defaults."""
        uv = _make_device()

        assert uv.od is None
        assert uv.device_ids is None
        assert uv.device is None
        assert uv.initialized is False
        assert uv.serial is None
        assert uv.model is None

        assert uv.blank_spectrum is None
        assert uv.dark_spectrum is None
        assert uv.raw_spectrum is None
        assert uv.absorbance_spectrum is None
        assert uv.spectra_sum is None
        assert uv.wavelengths is None

        assert uv.target_wavelengths == [409.0]
        assert uv.absorbance_at_target_wavelength is None

        assert uv._stop_flag is None
        assert uv._worker_thread is None
        assert uv._csv_file_path is None
        assert uv._csv_writer is None
        assert uv._start_time is None

        assert uv.convergence_enabled is False
        assert uv.spike_level == 0.2
        assert uv.convergence_threshold == 0.05
        assert uv.convergence_time == 5 * 60
        assert uv.max_outliers == 2
        assert uv._convergence_state == {
            "previous": None,
            "spike_seen": False,
            "converged_start": None,
            "outliers": [],
            "done": False,
        }

    def test_custom_target_wavelengths(self):
        """target_wavelengths passed at init are stored as floats."""
        uv = _make_device(target_wavelengths=[250, 300, 350])
        assert uv.target_wavelengths == [250.0, 300.0, 350.0]

    @pytest.mark.parametrize("kwarg, value", [
        ("integration_time", -1),
        ("num_scans", 0),
        ("measurement_interval", 0),
    ])
    def test_invalid_parameter_raises(self, kwarg, value):
        """Initialization with an invalid parameter raises ValueError."""
        with patch(_OCEAN_API_PATH, MagicMock()):
            with pytest.raises(ValueError):
                Ocean_Optics_UV_vis(output_dir=tempfile.mkdtemp(), **{kwarg: value})


# ---------------------------------------------------------------------------
# set_number_of_scans
# ---------------------------------------------------------------------------


class TestSetNumberOfScans:

    def test_set_number_of_scans(self):
        uv = _make_device()
        uv.set_number_of_scans(10)
        assert uv.num_scans == 10


# ---------------------------------------------------------------------------
# set_target_wavelength
# ---------------------------------------------------------------------------


class TestSetTargetWavelength:

    def test_set_target_wavelength(self):
        uv = _make_device()
        uv.set_target_wavelength("250.0;300.0;350.0")
        assert uv.target_wavelengths == [250.0, 300.0, 350.0]

        def test_set_target_wavelength_from_semicolon_string_parses_values(self):
            uv = _make_device()
            uv.set_target_wavelength("409;506")
            assert uv.target_wavelengths == [409.0, 506.0]

        def test_set_target_wavelength_from_single_string_parses_value(self):
            uv = _make_device()
            uv.set_target_wavelength("409")
            assert uv.target_wavelengths == [409.0]


# ---------------------------------------------------------------------------
# set_measurement_interval
# ---------------------------------------------------------------------------


class TestSetMeasurementInterval:

    def test_set_measurement_interval(self):
        uv = _make_device()
        uv.set_measurement_interval(30.0)
        assert uv.measurement_interval == 30.0

    def test_set_measurement_interval_int_converts_to_float(self):
        uv = _make_device()
        uv.set_measurement_interval(60)
        assert uv.measurement_interval == 60.0


# ---------------------------------------------------------------------------
# status()
# ---------------------------------------------------------------------------


class TestStatusParsing:

    def test_status_keys(self):
        """status() returns a dict with all expected keys."""
        uv = _make_device()
        result = uv.status()
        assert set(result.keys()) == {
            "initialized", "model", "serial",
            "integration_time_us", "num_scans", "targets_nm", "interval_s",
        }

    def test_status_defaults(self):
        """status() reflects unconnected default state."""
        uv = _make_device()
        result = uv.status()
        assert result["initialized"] is False
        assert result["model"] is None
        assert result["serial"] is None
        assert result["num_scans"] == 10
        assert result["targets_nm"] == [409.0]

    def test_status_reflects_updated_values(self):
        """status() reflects values changed via setters."""
        uv = _make_device()
        uv.set_number_of_scans(25)
        uv.set_target_wavelength("300.0;400.0")
        uv.set_measurement_interval(60.0)
        result = uv.status()
        assert result["num_scans"] == 25
        assert result["targets_nm"] == [300.0, 400.0]
        assert result["interval_s"] == 60.0
