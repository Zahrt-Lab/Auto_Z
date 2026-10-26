# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
Integration tests for Ocean Optics UV-Vis detector through GeneralExperimentMethod.

Every test goes through run_experiment() — no direct Ocean_Optics_UV_vis calls.
InstrumentManager is patched to inject an Ocean_Optics_UV_vis with mocked device.
"""

import numpy as np
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from methods.methods import GeneralExperimentMethod

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_uv_detector(tmp_path):
    """
    Ocean_Optics_UV_vis instance with all hardware calls mocked out.

    Pre-loaded state so measure_absorbance works without a prior record_blank:
      - blank_spectrum / raw_spectrum  : 2048-point float arrays
      - wavelengths                    : 200-900 nm linspace
      - absorbance_spectrum            : -log10(raw/blank) at all pixels (~0.301 AU)
      - initialized = True             : skips ensure_init() guard
    """
    from devices.industry_components.uv_detectors.uv_detector import Ocean_Optics_UV_vis

    # Patch the module-level OceanDirectAPI variable so __init__ won't raise.
    with patch(
        "devices.industry_components.uv_detectors.uv_detector.OceanDirectAPI",
        MagicMock(),
    ):
        uv = Ocean_Optics_UV_vis(output_dir=str(tmp_path / "uv_output"))

    # --- hardware layer mock (equivalent to pump.ser) ---
    wavelengths = np.linspace(200, 900, 2048)
    blank = np.ones(2048) * 10000.0
    raw = np.ones(2048) * 5000.0

    mock_device = MagicMock()
    mock_device.get_formatted_spectrum.return_value = raw.tolist()
    mock_device.get_wavelengths.return_value = wavelengths.tolist()
    mock_device.get_serial_number.return_value = "TEST123"
    mock_device.get_model.return_value = "HR2000"
    mock_device.get_scans_to_average.return_value = 10

    uv.device = mock_device
    uv.initialized = True
    uv.model = "HR2000"
    uv.serial = "TEST123"

    # connect() calls OceanDirectAPI() which is None on non-Windows/SDK-less systems.
    # set_integration_time() hits `except OceanDirectError` where OceanDirectError is also
    # None, raising TypeError.  Stub both so action-level tests stay at the right scope.
    uv.connect = MagicMock()
    uv.set_integration_time = MagicMock()

    # Pre-load spectrum state so measure_absorbance doesn't need record_blank first.
    uv.wavelengths = wavelengths
    uv.blank_spectrum = blank
    uv.raw_spectrum = raw
    uv.absorbance_spectrum = -np.log10(raw / blank)  # ~0.301 AU

    return uv


def _build_gm(tmp_path, mock_uv_detector, method_rows: str) -> GeneralExperimentMethod:
    """Create a GeneralExperimentMethod with InstrumentManager patched to inject mock_uv_detector."""
    method_csv = tmp_path / "method.csv"
    method_csv.write_text("Component,Action,Parameters,Notes,delay\n" + method_rows)
    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text("InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n")

    def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
        self_im.instrument_config_file = instrument_config_file
        self_im.experiment_subdir = experiment_subdir
        self_im.instruments = {"OceanOptics_1": mock_uv_detector}
        self_im.instrument_types = {"OceanOptics_1": "OceanOptics_UVVis"}
        self_im.instrument_config = None

    with patch("methods.instrument_manager.InstrumentManager.__init__", _fake_im_init):
        return GeneralExperimentMethod(
            input_file=str(method_csv),
            instrument_config_file=str(config_csv),
            output_dir=str(tmp_path / "output"),
            instrument_control_file=str(tmp_path / "instrument_control.txt"),
        )


def _run(gm: GeneralExperimentMethod) -> pd.DataFrame:
    """Run the experiment and return the log as a DataFrame."""
    with patch("methods.status_monitor.StatusMonitor.start"), patch("time.sleep"):
        gm.run_experiment()
    return pd.read_csv(gm.logger.log_filename)


# ---------------------------------------------------------------------------
# Log output
# ---------------------------------------------------------------------------


class TestLogOutput:

    def test_init_logged_ok(self, tmp_path, mock_uv_detector):
        gm = _build_gm(tmp_path, mock_uv_detector, "OceanOptics_1,init,,,0.5\n")
        log = _run(gm)
        row = log[(log["Component"] == "OceanOptics_1") & (log["Action"] == "init")]
        assert row["Output"].str.contains("OK", na=False).any()

    def test_record_blank_logged_ok(self, tmp_path, mock_uv_detector):
        gm = _build_gm(tmp_path, mock_uv_detector, "OceanOptics_1,record_blank,,,0.5\n")
        log = _run(gm)
        row = log[
            (log["Component"] == "OceanOptics_1") & (log["Action"] == "record_blank")
        ]
        assert row["Output"].str.contains("OK", na=False).any()

    def test_record_dark_logged_ok(self, tmp_path, mock_uv_detector):
        # Dark spectrum must have intensity <= threshold (500). Override mock to return ~10.
        mock_uv_detector.device.get_formatted_spectrum.return_value = [10.0] * 2048
        gm = _build_gm(tmp_path, mock_uv_detector, "OceanOptics_1,record_dark,,,0.5\n")
        log = _run(gm)
        row = log[
            (log["Component"] == "OceanOptics_1") & (log["Action"] == "record_dark")
        ]
        assert row["Output"].str.contains("OK", na=False).any()

    def test_measure_absorbance_logged(self, tmp_path, mock_uv_detector):
        gm = _build_gm(
            tmp_path, mock_uv_detector, "OceanOptics_1,measure_absorbance,,,0.5\n"
        )
        log = _run(gm)
        row = log[
            (log["Component"] == "OceanOptics_1")
            & (log["Action"] == "measure_absorbance")
        ]
        # Executor logs "A=<value>" for a successful measurement
        assert row["Output"].str.contains("A=", na=False).any()

    def test_status_logged(self, tmp_path, mock_uv_detector):
        gm = _build_gm(tmp_path, mock_uv_detector, "OceanOptics_1,status,,,0.5\n")
        log = _run(gm)
        row = log[(log["Component"] == "OceanOptics_1") & (log["Action"] == "status")]
        assert not row.empty

    def test_start_stop_continuous_logged(self, tmp_path, mock_uv_detector):
        rows = (
            "OceanOptics_1,start_continuous,,,0.5\n"
            "OceanOptics_1,stop_continuous,,,0.5\n"
        )
        gm = _build_gm(tmp_path, mock_uv_detector, rows)
        log = _run(gm)
        assert (
            log[(log["Action"] == "start_continuous")]["Output"]
            .str.contains("OK", na=False)
            .any()
        )
        assert (
            log[(log["Action"] == "stop_continuous")]["Output"]
            .str.contains("OK", na=False)
            .any()
        )

    def test_set_params_logged_ok(self, tmp_path, mock_uv_detector):
        # extract_uv_detector_parameters splits on commas; semicolons are only for
        # target_wavelengths list values.  Wrap in CSV quotes to protect the commas.
        params = "integration_time=50000,num_scans=5,measurement_interval=10"
        gm = _build_gm(
            tmp_path, mock_uv_detector, f'OceanOptics_1,set_params,"{params}",,0.5\n'
        )
        log = _run(gm)
        row = log[
            (log["Component"] == "OceanOptics_1")
            & (log["Action"] == "set_params")
            & (log["Parameters"] == params)
        ]
        assert row["Output"].str.contains("OK", na=False).any()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:

    def test_unknown_action_logged_as_error(self, tmp_path, mock_uv_detector):
        gm = _build_gm(
            tmp_path, mock_uv_detector, "OceanOptics_1,nonexistent_action,,,0.5\n"
        )
        with patch("methods.status_monitor.StatusMonitor.start"), patch("time.sleep"):
            gm.run_experiment()
        log = pd.read_csv(gm.logger.log_filename)
        assert log["Output"].str.contains("skipped|FAILED|Error", na=False).any()
