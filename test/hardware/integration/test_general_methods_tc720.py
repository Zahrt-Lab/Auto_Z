# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Hardware integration tests for TC720 through GeneralExperimentMethod.

Every test goes through run_experiment() with a real TC720 device.
InstrumentManager is patched to inject the real tc720_device fixture.
StatusMonitor is patched to suppress background polling.
time.sleep is NOT patched — real delays are needed for serial I/O.

Safety constraints:
  - All set_temperature calls use 25°C (safe ambient default)
  - No wait_convergence calls (avoids multi-minute waits)
  - Teardown in conftest.py always returns to 25°C before closing

These tests are auto-skipped if no TC720 is detected.
"""

import re
import pytest
import pandas as pd
from unittest.mock import patch

from methods.methods import GeneralExperimentMethod

pytestmark = [pytest.mark.hardware, pytest.mark.tc720]

_IM_INIT = "methods.instrument_manager.InstrumentManager.__init__"
_SM_START = "methods.status_monitor.StatusMonitor.start"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_gm(tmp_path, tc720_device, method_rows: str) -> GeneralExperimentMethod:
    """Create a GeneralExperimentMethod with InstrumentManager patched to inject tc720_device."""
    method_csv = tmp_path / "method.csv"
    method_csv.write_text("Component,Action,Parameters,Notes,delay\n" + method_rows)
    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text("InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n")

    def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
        self_im.instrument_config_file = instrument_config_file
        self_im.experiment_subdir = experiment_subdir
        self_im.instruments = {"TC720_1": tc720_device}
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


def _run(gm) -> pd.DataFrame:
    """Run the experiment and return the action log as a DataFrame."""
    with patch(_SM_START):
        gm.run_experiment()
    return pd.read_csv(gm.logger.log_filename)


# ---------------------------------------------------------------------------
# Safety test — full run must complete without exception
# ---------------------------------------------------------------------------


class TestSafetyHardware:

    def test_run_completes_without_exception(self, tmp_path, tc720_device):
        """run_experiment() with set_temperature + get_temperature must not raise."""
        gm = _build_gm(
            tmp_path,
            tc720_device,
            "TC720_1,set_temperature,temp=25.0,,0.5\n"
            "TC720_1,get_temperature,,,0.5\n",
        )
        _run(gm)  # must not raise error


# ---------------------------------------------------------------------------
# Log output — correct values written to the CSV log from real hardware
# ---------------------------------------------------------------------------


class TestLogOutputHardware:

    @pytest.fixture
    def log(self, tmp_path, tc720_device):
        gm = _build_gm(
            tmp_path,
            tc720_device,
            "TC720_1,set_temperature,temp=25.0,,0.5\n"
            "TC720_1,get_temperature,,,0.5\n",
        )
        return _run(gm)

    def test_set_temperature_row_logged(self, log):
        """set_temperature row must appear in the log with a non-empty Output."""
        row = log[
            (log["Component"] == "TC720_1") & (log["Action"] == "set_temperature")
        ]
        assert not row.empty, "set_temperature not found in log"
        assert str(row["Output"].iloc[0]).strip() != "", "set_temperature Output is empty"

    def test_get_temperature_logged_real_value(self, log):
        """get_temperature Output must contain a plausible float from the real device."""
        row = log[
            (log["Component"] == "TC720_1") & (log["Action"] == "get_temperature")
        ]
        assert not row.empty, "get_temperature not found in log"
        output = str(row["Output"].iloc[0])
        match = re.search(r"-?\d+\.\d+", output)
        assert match is not None, f"No float found in get_temperature Output: {output!r}"
        temp = float(match.group())
        assert -20.0 < temp < 150.0, (
            f"Temperature from real device out of plausible range: {temp}°C"
        )


# ---------------------------------------------------------------------------
# Error handling — unknown actions logged, not silently swallowed
# ---------------------------------------------------------------------------


class TestErrorHandlingHardware:

    def test_unknown_action_logged_as_error(self, tmp_path, tc720_device):
        """An unrecognised action must appear in the log as an Error, not be swallowed."""
        gm = _build_gm(tmp_path, tc720_device, "TC720_1,nonexistent_action,,,0.0\n")
        log = _run(gm)
        assert log["Output"].str.contains("Error", na=False).any(), (
            "Expected an Error entry in the log for an unknown action"
        )
