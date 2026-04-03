# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Integration tests for TC720 through GeneralExperimentMethod.

Every test goes through run_experiment() — no direct TC720 method calls.
InstrumentManager is patched to inject a TC720 with mocked serial.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from methods.methods import GeneralExperimentMethod
from conftest import make_tc720_response

_IM_INIT  = "methods.instrument_manager.InstrumentManager.__init__"
_SM_START = "methods.status_monitor.StatusMonitor.start"
_SLEEP    = "temperature_controller.tc720.tc720.time.sleep"


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_tc():
    """TC720 with mock serial, pre-loaded with enough read() responses."""
    from devices.industry_components.temperature_controller.tc720.tc720 import TC720
    tc = TC720(port="COM_TEST")
    ser = MagicMock()
    ser.is_open = True
    ser.read.side_effect = [make_tc720_response(25.0)] * 5 + [b''] * 10
    tc.ser = ser
    tc._connected = True
    return tc


def _build_gm(tmp_path, mock_tc, method_rows: str) -> GeneralExperimentMethod:
    """Create a GeneralExperimentMethod with InstrumentManager patched to inject mock_tc."""
    method_csv = tmp_path / "method.csv"
    method_csv.write_text(
        "Component,Action,Parameters,Notes,delay\n" + method_rows
    )
    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text("InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n")

    def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
        self_im.instrument_config_file = instrument_config_file
        self_im.experiment_subdir = experiment_subdir
        self_im.instruments = {"TC720_1": mock_tc}
        self_im.instrument_types = {"TC720_1": "Temperature"}
        self_im.instrument_config = None

    with patch(_IM_INIT, _fake_im_init):
        return GeneralExperimentMethod(
            input_file=str(method_csv),
            instrument_config_file=str(config_csv),
            output_dir=str(tmp_path / "output"),
            instrument_control_file=str(tmp_path / "instrument_control.txt"),
            dh2000_light_source_control_file=str(tmp_path / "dh2000_control.txt"),
        )


@pytest.fixture
def gm(tmp_path, mock_tc):
    return _build_gm(
        tmp_path, mock_tc,
        "TC720_1,set_temperature,temp=25.0,,0.0\n"
        "TC720_1,get_temperature,,,0.0\n",
    )


def _run(gm) -> pd.DataFrame:
    """Run the experiment and return the action log as a DataFrame."""
    with patch(_SM_START), patch(_SLEEP):
        gm.run_experiment()
    return pd.read_csv(gm.log_filename)

# ---------------------------------------------------------------------------
# Log output — correct values written to the CSV log
# ---------------------------------------------------------------------------

class TestLogOutput:

    def test_set_temperature_logged_with_value(self, gm):
        log = _run(gm)
        row = log[(log["Component"] == "TC720_1") & (log["Action"] == "set_temperature")]
        assert "25.0" in row["Output"].iloc[0]

    def test_get_temperature_logged_with_value(self, gm):
        log = _run(gm)
        row = log[(log["Component"] == "TC720_1") & (log["Action"] == "get_temperature")]
        assert "25.0" in row["Output"].iloc[0]


# ---------------------------------------------------------------------------
# Error handling — unknown actions logged, not silently swallowed
# ---------------------------------------------------------------------------

class TestErrorHandling:

    def test_unknown_action_logged_as_error(self, tmp_path, mock_tc):
        bad_gm = _build_gm(tmp_path, mock_tc, "TC720_1,nonexistent_action,,,0.0\n")
        with patch(_SM_START), patch(_SLEEP):
            bad_gm.run_experiment()
        log = pd.read_csv(bad_gm.log_filename)
        assert log["Output"].str.contains("Error", na=False).any()
