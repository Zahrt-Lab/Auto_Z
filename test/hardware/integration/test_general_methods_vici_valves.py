# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Andrew Zahrt
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
Integration tests for general methods that use VICI valves.

Every test goes through run_experiment() — no direct VICI valve method calls.
InstrumentManager is patched to inject the real vici_valve_device fixture so
commands travel through GeneralExperimentMethod → DeviceExecutor → ViciValve.

Safety constraint: movements are limited to positions 1–2 to minimise
plumbing changes during testing.
"""

import re
import pytest
import pandas as pd
from unittest.mock import patch

from methods.methods import GeneralExperimentMethod

pytestmark = [pytest.mark.hardware, pytest.mark.vici_valve]

_IM_INIT = "methods.instrument_manager.InstrumentManager.__init__"
_SM_START = "methods.status_monitor.StatusMonitor.start"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_gm(tmp_path, vici_valve_device, method_rows: str) -> GeneralExperimentMethod:
    """Create a GeneralExperimentMethod with InstrumentManager patched to inject vici_valve_device."""
    method_csv = tmp_path / "method.csv"
    method_csv.write_text("Component,Action,Parameters,Notes,delay\n" + method_rows)
    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text("InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n")

    def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
        self_im.instrument_config_file = instrument_config_file
        self_im.experiment_subdir = experiment_subdir
        self_im.instruments = {"VICI_VALVE_1": vici_valve_device}
        self_im.instrument_types = {"VICI_VALVE_1": "Valve"}
        self_im.instrument_config = None

    with patch(_IM_INIT, _fake_im_init):
        return GeneralExperimentMethod(
            input_file=str(method_csv),
            instrument_config_file=str(config_csv),
            output_dir=str(tmp_path / "output"),
            instrument_control_file=str(tmp_path / "instrument_control.txt"),
            dh2000_light_source_control_file=str(tmp_path / "dh2000_light_source_control.txt"),
        )


def _run(gm) -> pd.DataFrame:
    """Run the experiment and return the logged data as a DataFrame."""
    with patch(_SM_START):
        gm.run_experiment()
    return pd.read_csv(gm.logger.log_filename)


# ---------------------------------------------------------------------------
# Safety test — full run must complete without exception
# ---------------------------------------------------------------------------


class TestSafetyHardware:

    def test_full_run_completes_without_exception(self, tmp_path, vici_valve_device):
        """Full experiment with go_to_position + move_home must not raise."""
        gm = _build_gm(
            tmp_path,
            vici_valve_device,
            "VICI_VALVE_1,go_to_position,position=1,,0.5\n"
            "VICI_VALVE_1,go_to_position,position=2,,0.5\n"
            "VICI_VALVE_1,move_home,,,0.5\n"
            "VICI_VALVE_1,get_position,,,0.5\n"
        )
        _run(gm)  # must not raise


# ---------------------------------------------------------------------------
# Log output — correct values written to the CSV log from real hardware
# ---------------------------------------------------------------------------


class TestLogOutputHardware:

    @pytest.fixture
    def log(self, tmp_path, vici_valve_device):
        """Run a method with positions 1 and 2, move_home, get_position; return log."""
        gm = _build_gm(
            tmp_path,
            vici_valve_device,
            "VICI_VALVE_1,go_to_position,position=1,,0.5\n"
            "VICI_VALVE_1,go_to_position,position=2,,0.5\n"
            "VICI_VALVE_1,move_home,,,0.5\n"
            "VICI_VALVE_1,get_position,,,0.5\n"
        )
        return _run(gm)

    @pytest.mark.parametrize("position", [1, 2])
    def test_go_to_position_logged(self, log, position):
        """Each go_to_position command must appear in the log with its position parameter."""
        rows = log[
            (log["Action"] == "go_to_position") &
            (log["Parameters"].str.contains(f"position={position}", na=False))
        ]
        assert len(rows) == 1

    def test_move_home_logged(self, log):
        """move_home must appear exactly once in the log."""
        rows = log[log["Action"] == "move_home"]
        assert len(rows) == 1

    def test_get_position_logged_with_output(self, log):
        """get_position must appear in the log and return a non-empty output value."""
        rows = log[log["Action"] == "get_position"]
        assert len(rows) == 1
        assert str(rows.iloc[0]["Output"]).strip() != ""


# ---------------------------------------------------------------------------
# Error handling — invalid inputs must log errors without crashing
# ---------------------------------------------------------------------------


class TestErrorHandlingHardware:

    def test_unknown_action_logged_as_error(self, tmp_path, vici_valve_device):
        """An unrecognised action (e.g. 'spin') must log an error row, not raise."""
        gm = _build_gm(
            tmp_path,
            vici_valve_device,
            "VICI_VALVE_1,spin,,,0.5\n"
        )
        log = _run(gm)
        row = log[log["Action"] == "spin"]
        assert not row.empty
        assert "error" in str(row.iloc[0]["Output"]).lower()

    def test_invalid_position_logged_as_error(self, tmp_path, vici_valve_device):
        """position=0 is out of range (valid: 1–6); must log an error, not crash."""
        gm = _build_gm(
            tmp_path,
            vici_valve_device,
            "VICI_VALVE_1,go_to_position,position=0,,0.5\n"
        )
        log = _run(gm)
        row = log[log["Action"] == "go_to_position"]
        assert not row.empty
        assert "error" in str(row.iloc[0]["Output"]).lower()
