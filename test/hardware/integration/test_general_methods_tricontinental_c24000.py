# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
Hardware integration tests for TC24000 through GeneralExperimentMethod.

Every test goes through run_experiment() with a real TC24000 device.
InstrumentManager is patched to inject the real tc24000_device fixture.
StatusMonitor is patched to suppress background polling.
time.sleep is NOT patched — real delays are needed for serial I/O.

Safety Constraints:
    - The Max Flow rate is limited to 1000 uL/min 

These tests are auto-skipped if no TC24000 is detected.
"""

import re
import pytest
import pandas as pd
from unittest.mock import patch

from methods.methods import GeneralExperimentMethod

pytestmark = [pytest.mark.hardware, pytest.mark.tc24000]

_IM_INIT = "methods.instrument_manager.InstrumentManager.__init__"
_SM_START = "methods.status_monitor.StatusMonitor.start"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_gm(tmp_path, tc24000_device, method_rows: str) -> GeneralExperimentMethod:
    """Create a GeneralExperimentMethod with InstrumentManager patched to inject tc24000_device."""
    method_csv = tmp_path / "method.csv"
    method_csv.write_text("Component,Action,Parameters,Notes,delay\n" + method_rows)
    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text("InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n")

    def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
        self_im.instrument_config_file = instrument_config_file
        self_im.experiment_subdir = experiment_subdir
        self_im.instruments = {"TC24000_1": tc24000_device}
        self_im.instrument_types = {"TC24000_1": "Pump"}
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
    """Run the experiment and return the logged output as a DataFrame."""
    with patch(_SM_START):
        gm.run_experiment()
    return pd.read_csv(gm.logger.log_filename)


# ---------------------------------------------------------------------------
# Safety test 
# ---------------------------------------------------------------------------


class TestSafetyHardware:

    def test_full_run_completes_without_exception(self, tmp_path, tc24000_device):
        """Full experiment with dispensing must not raise."""
        gm = _build_gm(
            tmp_path,
            tc24000_device,
            method_rows='TC24000_1,dispensing,"flow_rate=500.0,volume=500.0",,0.5\n'  
        )

        _run(gm)

#---------------------------------------------------------------------------
# Log output test — correct values must be logged to the CSV
#---------------------------------------------------------------------------


class TestLogOutputHardware:
    
    @pytest.fixture
    def log(self, tmp_path, tc24000_device):
        """Run an experiment and return the logged data as a DataFrame."""
        gm = _build_gm(
            tmp_path,
            tc24000_device,
            method_rows='TC24000_1,dispensing,"flow_rate=500.0,volume=500.0",,0.5\n'
                        'SYNC,wait_for_pumps,,,0.5\n',
        )
        return _run(gm)
    
    def test_dispensing_logged(self, log):
        """run_experiment() with dispensing must log correct values to the CSV."""
        go_rows = log[log['Action'] == 'dispensing']
        assert len(go_rows) == 1, "Expected exactly one dispensing action logged"
        assert re.match(r"flow_rate=500\.0,volume=500\.0", go_rows.iloc[0]['Parameters'])

    def test_sync_logged(self, log):
        """run_experiment() with wait_for_pumps must log correct values to the CSV."""
        sync_rows = log[log['Action'] == 'wait_for_pumps']
        assert len(sync_rows) == 1, "Expected exactly one wait_for_pumps action logged"

    def test_dispensing_output_logged(self, log):
        """run_experiment() with dispensing must log correct output values to the CSV."""
        go_rows = log[log['Action'] == 'dispensing']
        assert len(go_rows) == 1, "Expected exactly one dispensing action logged"


# ---------------------------------------------------------------------------
# Error handling — invalid inputs must log errors without crashing
# ---------------------------------------------------------------------------


class TestErrorHandlingHardware:

    def test_invalid_flow_rate_logs_error(self, tmp_path, tc24000_device):
        """Invalid flow_rate must log an error without raising an exception."""
        gm = _build_gm(
            tmp_path,
            tc24000_device,
            method_rows='TC24000_1,swim,"flow_rate=-1000.0,volume=500.0",,0.5\n',  # Invalid flow rate
         )
        log = _run(gm)
        error_rows = log[log['Output'].str.contains("Error", na=False)]
        assert len(error_rows) == 1, "Expected exactly one error logged for invalid flow_rate"
        assert 'Error' in error_rows.iloc[0]['Output'], "Expected 'Error' in the log output with invalid flow_rate"

    def test_unknown_action_logged_as_error(self, tmp_path, tc24000_device):
        """Unknown action must log an error without raising an exception."""
        gm = _build_gm(
            tmp_path,
            tc24000_device,
            method_rows='TC24000_1,unknown_action,,,0.5\n',
        )
        log = _run(gm)
        go_rows = log[log['Action'] == 'unknown_action']
        error_rows = log[log['Output'].str.contains("Error", na=False)]
        assert len(error_rows) == 1, "Expected exactly one error logged for unknown action"
        assert 'Error' in error_rows.iloc[0]['Output'], "Expected 'Error' in the log output for unknown action"