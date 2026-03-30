"""
Integration tests for DH2000 through GeneralExperimentMethod.

Verifies the full pipeline:
  method CSV -> run_experiment() -> execute_dh2000() -> mock serial

InstrumentManager is patched to inject a DH2000LightSource with mocked serial.
StatusMonitor.start is patched to prevent a background thread from starting.
time.sleep and _drain inside the DH2000 module are patched to keep tests fast.
All output files land in pytest's tmp_path.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from datetime import datetime

from methods.methods import GeneralExperimentMethod
from methods.device_executors import DeviceExecutor
from uv_detectors.dh2000 import DH2000LightSource

_IM_INIT    = "methods.instrument_manager.InstrumentManager.__init__"
_SM_START   = "methods.status_monitor.StatusMonitor.start"
_SLEEP_PATH = "uv_detectors.dh2000.time.sleep"
_DRAIN_PATH = "uv_detectors.dh2000.DH2000LightSource._drain"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_dh():
    """
    DH2000LightSource with a mock serial port, pre-loaded with enough readline()
    responses for a method CSV of: shutter_open, status, plus shutdown status call.
    """
    dh = DH2000LightSource(port="COM_TEST", timeout=2.0)
    ser = MagicMock()
    ser.in_waiting = 0
    ser.readline.side_effect = (
        [b"OK\r\n"]                                                             # shutter_open OK
        + [b"Shutter: OPEN\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n"]  # status (method row)
        + [b"Shutter: OPEN\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n"]  # status (shutdown noop)
        + [b""] * 20
    )
    dh.ser = ser
    return dh


@pytest.fixture
def gm(tmp_path, mock_dh):
    """
    GeneralExperimentMethod with:
      - a 2-row method CSV (shutter_open / status)
      - InstrumentManager patched to inject mock_dh
      - all output files directed to tmp_path
    """
    method_csv = tmp_path / "method.csv"
    method_csv.write_text(
        "Component,Action,Parameters,Notes,delay\n"
        "DH2000_1,shutter_open,,,0.0\n"
        "DH2000_1,status,,,0.0\n"
    )

    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text(
        "InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n"
    )

    def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
        self_im.instrument_config_file = instrument_config_file
        self_im.experiment_subdir = experiment_subdir
        self_im.instruments = {"DH2000_1": mock_dh}
        self_im.instrument_types = {"DH2000_1": "DH2000"}
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
    """Run experiment with StatusMonitor, DH2000 sleep, and _drain patched."""
    with patch(_SM_START), patch(_SLEEP_PATH), patch(_DRAIN_PATH):
        gm.run_experiment()
    return pd.read_csv(gm.log_filename)


# ---------------------------------------------------------------------------
# Routing — does run_experiment() reach execute_dh2000()?
# ---------------------------------------------------------------------------

class TestRouting:

    def test_shutter_open_action_is_logged(self, gm):
        log = _run(gm)
        dh_rows = log[log["Component"] == "DH2000_1"]
        assert "shutter_open" in dh_rows["Action"].values

    def test_status_action_is_logged(self, gm):
        log = _run(gm)
        dh_rows = log[log["Component"] == "DH2000_1"]
        assert "status" in dh_rows["Action"].values

    def test_no_device_not_found_errors(self, gm):
        """DH2000_1 must always be resolved from instruments."""
        log = _run(gm)
        not_found = log[log["Output"].str.contains("not found", na=False)]
        assert len(not_found) == 0

    def test_both_actions_logged(self, gm):
        log = _run(gm)
        dh_rows = log[log["Component"] == "DH2000_1"]
        assert len(dh_rows) >= 2


# ---------------------------------------------------------------------------
# Serial commands — correct bytes reach the mock device
# ---------------------------------------------------------------------------

class TestSerialCommands:

    def test_shutter_open_sends_o_byte(self, gm, mock_dh):
        ser = mock_dh.ser
        _run(gm)
        written = [c.args[0] for c in ser.write.call_args_list]
        assert b"o" in written, f"Expected shutter_open 'o' in {written}"

    def test_status_sends_s_byte(self, gm, mock_dh):
        ser = mock_dh.ser
        _run(gm)
        written = [c.args[0] for c in ser.write.call_args_list]
        assert b"s" in written, f"Expected status 's' in {written}"


# ---------------------------------------------------------------------------
# Log output — correct values written to CSV
# ---------------------------------------------------------------------------

class TestLogOutput:

    def test_shutter_open_logs_ok(self, gm):
        log = _run(gm)
        row = log[(log["Component"] == "DH2000_1") & (log["Action"] == "shutter_open")]
        assert len(row) > 0
        assert "OK" in row["Output"].iloc[0]

    def test_status_output_contains_dict_keys(self, gm):
        log = _run(gm)
        row = log[(log["Component"] == "DH2000_1") & (log["Action"] == "status")]
        assert len(row) > 0
        output = row["Output"].iloc[0]
        assert "shutter_open" in output

    def test_shutdown_noop_is_logged(self, gm):
        """On success, shutdown() logs shutdown_success_noop for the DH2000."""
        log = _run(gm)
        assert "shutdown_success_noop" in log["Action"].values


# ---------------------------------------------------------------------------
# Error handling — unknown actions logged, not silently swallowed
# ---------------------------------------------------------------------------

class TestErrorHandling:

    def test_unknown_action_logged_as_error(self, tmp_path, mock_dh):
        method_csv = tmp_path / "bad_method.csv"
        method_csv.write_text(
            "Component,Action,Parameters,Notes,delay\n"
            "DH2000_1,nonexistent_action,,,0.0\n"
        )
        config_csv = tmp_path / "instruments.csv"
        config_csv.write_text(
            "InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n"
        )

        def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
            self_im.instrument_config_file = instrument_config_file
            self_im.experiment_subdir = experiment_subdir
            self_im.instruments = {"DH2000_1": mock_dh}
            self_im.instrument_types = {"DH2000_1": "DH2000"}
            self_im.instrument_config = None

        # Reload mock_dh readline for shutdown status call
        mock_dh.ser.readline.side_effect = (
            [b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n"] * 5
            + [b""] * 10
        )

        with patch(_IM_INIT, _fake_im_init):
            bad_gm = GeneralExperimentMethod(
                input_file=str(method_csv),
                instrument_config_file=str(config_csv),
                output_dir=str(tmp_path / "output"),
                instrument_control_file=str(tmp_path / "instrument_control.txt"),
                dh2000_light_source_control_file=str(tmp_path / "dh2000_control.txt"),
            )

        with patch(_SM_START), patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            bad_gm.run_experiment()

        log = pd.read_csv(bad_gm.log_filename)
        error_rows = log[log["Output"].str.contains("Error", na=False)]
        assert len(error_rows) > 0, "Expected at least one Error row in the log"


# ---------------------------------------------------------------------------
# DeviceExecutor unit — test execute_dh2000() in isolation
# ---------------------------------------------------------------------------

class TestExecuteDh2000:
    """
    Tests DeviceExecutor.execute_dh2000() directly, bypassing
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

    def _make_dh(self, readline_responses: list) -> DH2000LightSource:
        dh = DH2000LightSource(port="COM_TEST", timeout=2.0)
        ser = MagicMock()
        ser.in_waiting = 0
        ser.readline.side_effect = readline_responses + [b""] * 30
        dh.ser = ser
        return dh

    def test_shutter_open_calls_device(self, executor):
        dh = self._make_dh([b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            executor.execute_dh2000("shutter_open", "", "DH2000_1", dh)
        dh.ser.write.assert_called_once_with(b"o")

    def test_shutter_close_calls_device(self, executor):
        dh = self._make_dh([b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            executor.execute_dh2000("shutter_close", "", "DH2000_1", dh)
        dh.ser.write.assert_called_once_with(b"c")

    def test_halogen_toggle_calls_device(self, executor):
        dh = self._make_dh([b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            executor.execute_dh2000("halogen_toggle", "", "DH2000_1", dh)
        dh.ser.write.assert_called_once_with(b"h")

    def test_deuterium_toggle_calls_device(self, executor):
        dh = self._make_dh([b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            executor.execute_dh2000("deuterium_toggle", "", "DH2000_1", dh)
        dh.ser.write.assert_called_once_with(b"d")

    def test_status_is_logged(self, executor):
        dh = self._make_dh([
            b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n",
        ])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            executor.execute_dh2000("status", "", "DH2000_1", dh)
        assert any(e["action"] == "status" for e in executor._logged)

    def test_status_output_contains_dict_keys(self, executor):
        dh = self._make_dh([
            b"Shutter: OPEN\r\n", b"Halogen: ON\r\n", b"Deuterium: OFF\r\n",
        ])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            executor.execute_dh2000("status", "", "DH2000_1", dh)
        output = executor._logged[-1]["output"]
        assert "shutter_open" in output

    def test_safe_shutdown_is_logged(self, executor):
        dh = self._make_dh(
            [b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n"] * 5
        )
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            executor.execute_dh2000("safe_shutdown", "", "DH2000_1", dh)
        assert any(e["action"] == "safe_shutdown" for e in executor._logged)

    def test_safe_shutdown_output_contains_shutdown_message(self, executor):
        dh = self._make_dh(
            [b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n"] * 5
        )
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            executor.execute_dh2000("safe_shutdown", "", "DH2000_1", dh)
        output = executor._logged[-1]["output"]
        assert "Shutdown" in output

    def test_unknown_action_logs_error(self, executor):
        """execute_dh2000 logs the error AND re-raises ValueError for unknown actions."""
        dh = self._make_dh([])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            with pytest.raises(ValueError, match="Unknown DH2000 action"):
                executor.execute_dh2000("bad_action", "", "DH2000_1", dh)
        assert any("Error" in e["output"] for e in executor._logged)

    def test_all_toggle_commands_log_ok(self, executor):
        """shutter_open, shutter_close, halogen_toggle, deuterium_toggle all log 'OK'."""
        for action, cmd in [
            ("shutter_open",      b"o"),
            ("shutter_close",     b"c"),
            ("halogen_toggle",    b"h"),
            ("deuterium_toggle",  b"d"),
        ]:
            dh = self._make_dh([b"OK\r\n"])
            with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
                executor.execute_dh2000(action, "", "DH2000_1", dh)
            last = executor._logged[-1]
            assert last["action"] == action
            assert "OK" in last["output"], f"{action} output should contain OK"
