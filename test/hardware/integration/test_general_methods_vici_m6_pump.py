# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Hardware integration tests for VICI M6 Pump through GeneralExperimentMethod.

Every test goes through run_experiment() with a real VICI M6 Pump device.
InstrumentManager is patched to inject the real vici_m6_pump_device fixture.
StatusMonitor is patched to suppress background polling.
time.sleep is NOT patched — real delays are needed for serial I/O.

Safety constraints:
  - Max Flow rate is limited to 1000 uL/min (well below recommended max of 5000 uL/min)

These tests are auto-skipped if no VICI M6 Pump is detected.
"""

import re
import pytest
import pandas as pd
from unittest.mock import patch

from methods.methods import GeneralExperimentMethod

pytestmark = [pytest.mark.hardware, pytest.mark.vici_m6_pump]

_IM_INIT = "methods.instrument_manager.InstrumentManager.__init__"
_SM_START = "methods.status_monitor.StatusMonitor.start"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_gm(tmp_path, vici_m6_pump_device, method_rows: str) -> GeneralExperimentMethod:
    """Create a GeneralExperimentMethod with InstrumentManager patched to inject vici_m6_pump_device."""
    method_csv = tmp_path / "method.csv"
    method_csv.write_text("Component,Action,Parameters,Notes,delay\n" + method_rows)
    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text("InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n")

    def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
        self_im.instrument_config_file = instrument_config_file
        self_im.experiment_subdir = experiment_subdir
        self_im.instruments = {"VICI_M6_PUMP_1": vici_m6_pump_device}
        self_im.instrument_types = {"VICI_M6_PUMP_1": "Pump"}
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


#---------------------------------------------------------------------------
# Safety test — full run must complete without exception
#---------------------------------------------------------------------------


class TestSafetyHardware:

    def test_full_run_completes_without_exception(self, tmp_path, vici_m6_pump_device):
        """run_experiment() with dispensing and start must not raise."""
        gm = _build_gm(
            tmp_path,
            vici_m6_pump_device,
            method_rows=(
                'VICI_M6_PUMP_1,dispensing,"flow_rate=500.0,volume=500.0",,0.5\n'
                'SYNC,wait_for_pumps,,,0.5\n'
            ),
        )
        _run(gm)  # must not raise error


#---------------------------------------------------------------------------
# Log output — correct values written to the CSV log from real hardware
#---------------------------------------------------------------------------


class TestLogOutputHardware:

    @pytest.fixture
    def log(self, tmp_path, vici_m6_pump_device):
        """run_experiment() with dispensing must log correct values to the CSV."""
        gm = _build_gm(
            tmp_path,
            vici_m6_pump_device,
            method_rows='VICI_M6_PUMP_1,dispensing,"flow_rate=500.0,volume=500.0",,0.5\n'
                        'SYNC,wait_for_pumps,,,0.5\n',
        )
        return _run(gm)
    
    def test_dispensing_logged(self, log):
        """run_experiment() with dispensing must log correct values to the CSV."""
        go_rows = log[log['Action'] == 'dispensing']
        assert len(go_rows) == 1, "Expected exactly one dispensing action logged"
        assert re.match(r"flow_rate=500\.0,volume=500\.0", go_rows.iloc[0]['Parameters'])

    def test_sync_logged(self, log):
        """run_experiment() with wait_for_pumps must log the SYNC action."""
        sync_rows = log[log['Action'] == 'wait_for_pumps']
        assert len(sync_rows) == 1, "Expected exactly one wait_for_pumps action logged"

    def test_dispensing_output_logged(self, log):
        """dispensing action must have a non-empty Output logged."""
        go_rows = log[log['Action'] == 'dispensing']
        assert len(go_rows) == 1, "Expected exactly one dispensing action logged"

# ---------------------------------------------------------------------------
# Error handling — invalid inputs must log errors without crashing
# ---------------------------------------------------------------------------


class TestErrorHandlingHardware:

    def test_unknown_action_logged_as_error(self, tmp_path, vici_m6_pump_device):
        """Unknown action must be logged as an error, not silently swallowed."""
        gm = _build_gm(
            tmp_path,
            vici_m6_pump_device,
            method_rows='VICI_M6_PUMP_1,fly,,,0.5\n',
        )
        log = _run(gm)
        error_rows = log[log['Action'] == 'fly']
        assert len(error_rows) == 1, "Expected exactly one fly logged"
        assert 'Error' in error_rows.iloc[0]['Output'], "Expected error message in Output for fly"

    def test_invalid_parameters_logged_as_error(self, tmp_path, vici_m6_pump_device):
        """Invalid parameters must be logged as an error, not silently swallowed."""
        gm = _build_gm(
            tmp_path,
            vici_m6_pump_device,
            method_rows='VICI_M6_PUMP_1,dispensing,"flow_rate=-100.0,volume=-500.0",,0.5\n',
        )
        log = _run(gm)
        go_rows = log[log['Action'] == 'dispensing']
        assert len(go_rows) == 1, "Expected exactly one dispensing action logged"
        assert 'error' in go_rows.iloc[0]['Output'], "Expected error message in Output for invalid parameters"