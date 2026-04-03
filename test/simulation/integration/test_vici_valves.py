# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

'''
Integration tests for VICI valves through GeneralExperimentMethod.

Every test goes through the run_experiment() no direct VICI valve method calls.
InstrumentManager is patched to inject a VICI valve with mocked serial.
'''

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from methods.methods import GeneralExperimentMethod
from conftest import make_vici_valve_response


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_vici_valve():
    """VICI valve with mock serial, pre-loaded with enough read() responses."""
    from valves.vici_valves.vici_valves import ViciValve
    with patch('serial.Serial'):
        valve = ViciValve(port="COM_TEST", valve_type="6-way")
    ser = MagicMock()
    ser.is_open = True
    ser.read.side_effect = [make_vici_valve_response("Position: 1")] * 5 + [b''] * 10
    valve.ser = ser
    valve._connected = True
    return valve

def _build_gm(tmp_path, mock_vici_valve, method_rows: str) -> GeneralExperimentMethod:
    """Create a GeneralExperimentMethod with InstrumentManager patched to inject mock_vici_valve."""
    method_csv = tmp_path / "method.csv"
    method_csv.write_text(
        "Component,Action,Parameters,Notes,delay\n" + method_rows
    )
    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text("InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n")

    def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
        self_im.instrument_config_file = instrument_config_file
        self_im.experiment_subdir = experiment_subdir
        self_im.instruments = {"VICI_VALVE_1": mock_vici_valve}
        self_im.instrument_types = {"VICI_VALVE_1": "Valve"}
        self_im.instrument_config = None

    with patch("methods.instrument_manager.InstrumentManager.__init__", _fake_im_init):
        return GeneralExperimentMethod(
            input_file=str(method_csv),
            instrument_config_file=str(config_csv),
            output_dir=str(tmp_path / "output"),
            instrument_control_file=str(tmp_path / "instrument_control.txt"),
        )

@pytest.fixture
def set_position():
    """Default position for valves"""
    return 1

@pytest.fixture
def gm(tmp_path, mock_vici_valve, set_position):
    return _build_gm(
        tmp_path,
        mock_vici_valve,
        method_rows=f"VICI_VALVE_1,go_to_position,position={set_position},,0.5\n"
    )

def _run(gm: GeneralExperimentMethod) -> pd.DataFrame:
    """Run the experiment and return the log as a DataFrame."""
    with patch("methods.status_monitor.StatusMonitor.start"), patch("time.sleep"):
        gm.run_experiment()
    return pd.read_csv(gm.log_filename)

# ---------------------------------------------------------------------------
# Log output
# ---------------------------------------------------------------------------

class TestLogOutput:

    @pytest.mark.parametrize("set_position", [1, 3, 6])
    def test_go_to_position_logged_with_valid_position(self, gm, set_position):
        log = _run(gm)
        row = log[(log["Component"] == "VICI_VALVE_1") & 
                  (log["Action"] == f"go_to_position") &
                  (log["Parameters"] == f"position={set_position}")]
        assert row["Output"].str.contains(f"Moved valve to position {set_position}", na=False).any()

    @pytest.mark.parametrize("set_position", [0, 7, -1])
    def test_go_to_position_logged_with_invalid_position(self, gm, set_position):
        log = _run(gm)
        row = log[(log["Component"] == "VICI_VALVE_1") & 
                  (log["Action"] == f"go_to_position") &
                  (log["Parameters"] == f"position={set_position}")]
        assert log["Output"].str.contains("skipped|FAILED", na=False).any()

# ----------------------------------------------------------------------------
# Test Error Handling
# ---------------------------------------------------------------------------

class TestErrorHandling:

    def test_unknown_action_logged_as_error(self, tmp_path, mock_vici_valve):
        bad_gm = _build_gm(tmp_path, mock_vici_valve, "VICI_VALVE_1,nonexistent_action,,,0.5\n")
        with patch("methods.status_monitor.StatusMonitor.start"), patch("time.sleep"):
            bad_gm.run_experiment()
        log = pd.read_csv(bad_gm.log_filename)
        assert log["Output"].str.contains("Error", na=False).any()