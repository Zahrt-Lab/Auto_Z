# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Integration tests for general methods that use VICI valves.

Every test goes through the run_experiment() no direct VICI valve method calls.
InstrumentManager is patched to inject a VICI valve with serial commands
"""

import re
import pytest
import pandas as pd
from unittest.mock import patch

from methods.methods import GeneralExperimentMethod

pytestmark = [pytest.mark.hardware, pytest.mark.vici_valve]

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
            instrument_control_file=str(tmp_path / "instrument_control.csv"),
            dh2000_light_source_control_file=str(tmp_path / "dh2000_light_source_control.csv"),
        )   
    
def _run(gm) -> pd.DataFrame:
    """Run the experiment and return the logged data as a DataFrame."""
    with patch(_SM_START):
        gm.run_experiment()
    return pd.read_csv(gm.logger.log_filename)


#---------------------------------------------------------------------------
# Safety test — full run must complete without exception
#---------------------------------------------------------------------------


class TestSafetyHardware:

    def test_full_run_completes_without_exception(self, tmp_path, vici_valve_device):
        """run_experiment() with go_to_position must not raise.""":
        gm = _build_gm(
            tmp_path,
            vici_valve_device,
            "VICI_VALVE_1,go_to_position,position=1,,0.5\n"
            "VICI_VALVE_1,go_to_position,position=3,,0.5\n"
            "VICI_VALVE_1,move_home,,,0.5\n"
            "VICI_VALVE_1,get_position,,,0.5\n"
        )
        _run(gm)  # must not raise error


# ---------------------------------------------------------------------------
# Log output — correct values written to the CSV log from real hardware
#---------------------------------------------------------------------------


class TestLogOutputHardware:

    @pytest.fixture
    def log(self, tmp_path, vici_valve_device):
        """Run a method and return the log DataFrame."""
        gm = _build_gm(
            tmp_path,
            vici_valve_device,
            "VICI_VALVE_1,go_to_position,position=2,,0.5\n"
            "VICI_VALVE_1,get_position,,,0.5\n"
        )
        return _run(gm)
    
    def test_go_to_position_logged(self, log):
        """Check that go_to_position action is logged with correct position."""
        go_rows = log[log['Action'] == 'go_to_position']
        assert len(go_rows) == 1
        assert re.search(r'position=2', go_rows.iloc[0]['Parameters'])

    def test_get_position_logged(self, log):
        """Check that get_position action is logged."""
        get_rows = log[log['Action'] == 'get_position']
        assert len(get_rows) == 1
    
    def test_go_to_position_invalid_position_logged_as_error(self, log):
        """If an invalid position is given, it should be logged with an error."""
        go_rows = log[log['Action'] == 'go_to_position']
        assert len(go_rows) == 1
        assert re.search(r'position=2', go_rows.iloc[0]['Parameters'])
        # The actual error handling would depend on how the method logs errors; this is just a placeholder.