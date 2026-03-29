"""
Integration tests for TC720 through GeneralExperimentMethod.

Verifies the full pipeline:
  method CSV -> run_experiment() -> execute_temperature() -> mock serial

InstrumentManager is patched to inject a TC720 with mocked serial.
StatusMonitor.start is patched to prevent a background thread from starting.
time.sleep inside the TC720 module is patched to keep the suite fast.
All output files land in pytest's tmp_path.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from datetime import datetime

from methods.methods import GeneralExperimentMethod
from methods.device_executors import DeviceExecutor
from temperature_controller.tc720.tc720 import TC720

_IM_INIT    = "methods.instrument_manager.InstrumentManager.__init__"
_SM_START   = "methods.status_monitor.StatusMonitor.start"
_SLEEP_PATH = "temperature_controller.tc720.tc720.time.sleep"


def _make_response(temp_celsius: float) -> bytes:
    """Build a valid 8-byte TC720 response for a given temperature."""
    val = int(temp_celsius * 100)
    if val < 0:
        val += 0x10000
    dddd = format(val, '04x')
    checksum = format(sum(ord(c) for c in dddd) & 0xFF, '02x')
    return ('*' + dddd + checksum + '\r').encode('ascii')


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_tc():
    """TC720 with a mock serial port, pre-loaded with enough read() responses."""
    tc = TC720(port="COM_TEST")
    ser = MagicMock()
    ser.is_open = True
    ser.read.side_effect = (
        [_make_response(25.0)]   +  # get_temperature() in method CSV
        [_make_response(25.0)]   +  # possible extra call (e.g. status monitor)
        [b''] * 10
    )
    tc.ser = ser
    tc._connected = True
    return tc


@pytest.fixture
def gm(tmp_path, mock_tc):
    """
    GeneralExperimentMethod with:
      - a 2-row method CSV  (set_temperature / get_temperature)
      - InstrumentManager patched to inject mock_tc
      - all output files directed to tmp_path
    """
    method_csv = tmp_path / "method.csv"
    method_csv.write_text(
        "Component,Action,Parameters,Notes,delay\n"
        "TC720_1,set_temperature,temp=25.0,,0.0\n"
        "TC720_1,get_temperature,,,0.0\n"
    )

    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text(
        "InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n"
    )

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


def _run(gm) -> pd.DataFrame:
    """Run experiment with StatusMonitor and TC720 sleep patched, return log as DataFrame."""
    with patch(_SM_START), patch(_SLEEP_PATH):
        gm.run_experiment()
    return pd.read_csv(gm.log_filename)


# ---------------------------------------------------------------------------
# Routing — does run_experiment() reach execute_temperature()?
# ---------------------------------------------------------------------------

class TestRouting:

    def test_set_temperature_action_is_logged(self, gm):
        log = _run(gm)
        tc_rows = log[log["Component"] == "TC720_1"]
        assert "set_temperature" in tc_rows["Action"].values

    def test_get_temperature_action_is_logged(self, gm):
        log = _run(gm)
        tc_rows = log[log["Component"] == "TC720_1"]
        assert "get_temperature" in tc_rows["Action"].values

    def test_no_device_not_found_errors(self, gm):
        """TC720_1 must always be resolved from instruments."""
        log = _run(gm)
        not_found = log[log["Output"].str.contains("not found", na=False)]
        assert len(not_found) == 0

    def test_both_actions_logged(self, gm):
        log = _run(gm)
        tc_rows = log[log["Component"] == "TC720_1"]
        assert len(tc_rows) >= 2


# ---------------------------------------------------------------------------
# Serial commands — correct bytes reach the mock device
# ---------------------------------------------------------------------------

class TestSerialCommands:

    def test_set_temperature_sends_correct_command(self, gm, mock_tc):
        ser = mock_tc.ser
        _run(gm)
        written = [c.args[0] for c in ser.write.call_args_list]
        assert b'*1c09c494\r' in written, f"Expected 25°C command in {written}"

    def test_get_temperature_sends_query_to_device(self, gm, mock_tc):
        ser = mock_tc.ser
        _run(gm)
        written = [c.args[0] for c in ser.write.call_args_list]
        # Sensor 1 query command
        assert b'*01000021\r' in written, f"Expected sensor-1 query in {written}"


# ---------------------------------------------------------------------------
# Log output — correct values written to CSV
# ---------------------------------------------------------------------------

class TestLogOutput:

    def test_set_temperature_output_contains_temperature(self, gm):
        log = _run(gm)
        row = log[(log["Component"] == "TC720_1") & (log["Action"] == "set_temperature")]
        assert len(row) > 0
        assert "25.0" in row["Output"].iloc[0]

    def test_get_temperature_output_contains_temperature_value(self, gm):
        log = _run(gm)
        row = log[(log["Component"] == "TC720_1") & (log["Action"] == "get_temperature")]
        assert len(row) > 0
        # Output is "Current temperature: 25.0°C"
        assert "25.0" in row["Output"].iloc[0]


# ---------------------------------------------------------------------------
# Error handling — unknown actions logged, not silently swallowed
# ---------------------------------------------------------------------------

class TestErrorHandling:

    def test_unknown_action_logged_as_error(self, tmp_path, mock_tc):
        """An unrecognised action must appear in the log as an Error."""
        method_csv = tmp_path / "bad_method.csv"
        method_csv.write_text(
            "Component,Action,Parameters,Notes,delay\n"
            "TC720_1,nonexistent_action,,,0.0\n"
        )
        config_csv = tmp_path / "instruments.csv"
        config_csv.write_text(
            "InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n"
        )

        def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
            self_im.instrument_config_file = instrument_config_file
            self_im.experiment_subdir = experiment_subdir
            self_im.instruments = {"TC720_1": mock_tc}
            self_im.instrument_types = {"TC720_1": "Temperature"}
            self_im.instrument_config = None

        with patch(_IM_INIT, _fake_im_init):
            bad_gm = GeneralExperimentMethod(
                input_file=str(method_csv),
                instrument_config_file=str(config_csv),
                output_dir=str(tmp_path / "output"),
                instrument_control_file=str(tmp_path / "instrument_control.txt"),
                dh2000_light_source_control_file=str(tmp_path / "dh2000_control.txt"),
            )

        with patch(_SM_START), patch(_SLEEP_PATH):
            bad_gm.run_experiment()

        log = pd.read_csv(bad_gm.log_filename)
        error_rows = log[log["Output"].str.contains("Error", na=False)]
        assert len(error_rows) > 0, "Expected at least one Error row in the log"


# ---------------------------------------------------------------------------
# DeviceExecutor unit — test execute_temperature() in isolation
# ---------------------------------------------------------------------------

class TestExecuteTemperature:
    """
    Tests DeviceExecutor.execute_temperature() directly, bypassing
    GeneralExperimentMethod entirely.
    """

    @pytest.fixture
    def executor(self):
        logged = []

        def _log(component, action, params, output, notes=""):
            logged.append({
                "component": component, "action": action,
                "params": params, "output": str(output),
            })

        ex = DeviceExecutor(
            bed_layouts={},
            log_callback=_log,
            start_time=datetime.now(),
            continue_flag_getter=lambda: True,
        )
        ex._logged = logged
        return ex

    def test_set_temperature_calls_device(self, executor, mock_tc):
        executor.execute_temperature("set_temperature", "temp=25.0", "TC720_1", mock_tc)
        mock_tc.ser.write.assert_called_with(b'*1c09c494\r')

    def test_set_temperature_is_logged(self, executor, mock_tc):
        executor.execute_temperature("set_temperature", "temp=25.0", "TC720_1", mock_tc)
        assert any(e["action"] == "set_temperature" for e in executor._logged)

    def test_get_temperature_calls_device(self, executor, mock_tc):
        mock_tc.ser.read.return_value = _make_response(25.0)
        with patch(_SLEEP_PATH):
            executor.execute_temperature("get_temperature", "", "TC720_1", mock_tc)
        mock_tc.ser.write.assert_called_once()  # query was sent

    def test_get_temperature_is_logged(self, executor, mock_tc):
        mock_tc.ser.read.return_value = _make_response(25.0)
        with patch(_SLEEP_PATH):
            executor.execute_temperature("get_temperature", "", "TC720_1", mock_tc)
        assert any(e["action"] == "get_temperature" for e in executor._logged)

    def test_unknown_action_logs_error(self, executor, mock_tc):
        executor.execute_temperature("bad_action", "", "TC720_1", mock_tc)
        assert any("Error" in e["output"] for e in executor._logged)

    def test_wait_convergence_converges_when_in_range(self, executor, mock_tc):
        """
        wait_convergence must return True and log success when the temperature
        is already within tolerance. Uses duration=0 so no stability wait needed.
        """
        mock_tc.ser.read.return_value = _make_response(25.0)
        # Patch time.sleep (TC720) and time.time to immediately report convergence
        with patch(_SLEEP_PATH), \
             patch("methods.device_executors.time.sleep"), \
             patch("methods.device_executors.time.time", side_effect=[0.0, 1.0, 2.0]):
            executor.execute_temperature(
                "wait_convergence",
                "target_temp=25.0, tolerance=2.0, duration=0.0",
                "TC720_1",
                mock_tc,
            )
        converge_logs = [e for e in executor._logged
                         if "converged" in e["output"].lower() or "wait_convergence" in e["action"]]
        assert len(converge_logs) > 0
