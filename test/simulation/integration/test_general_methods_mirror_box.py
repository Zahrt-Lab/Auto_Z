"""
Integration tests for MirrorBox365nm through GeneralExperimentMethod.

Verifies the full pipeline:
  method CSV -> run_experiment() -> execute_mirror_box() -> mock serial

InstrumentManager is patched to inject a MirrorBox365nm with mocked serial.
StatusMonitor.start is patched to prevent a background thread from starting.
All output files land in pytest's tmp_path.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from datetime import datetime

from methods.methods import GeneralExperimentMethod
from methods.device_executors import DeviceExecutor
from devices.custom_components.light_source.mirror_box_365nm.mirror_box_365nm import (
    MirrorBox365nm,
)

_IM_INIT = "methods.instrument_manager.InstrumentManager.__init__"
_SM_START = "methods.status_monitor.StatusMonitor.start"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_mb():
    """MirrorBox365nm with a mock serial port, pre-loaded with enough responses."""
    mb = MirrorBox365nm(port="COM_TEST")
    ser = MagicMock()
    ser.timeout = 2.0
    ser.in_waiting = 0
    ser.readline.side_effect = (
        [b"OK (dimmer set)\r\n"]  # set_dimmer(200)
        + [
            b"Light1: ON | Light2: ON | DimmerPWM: 200\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ]  # status()
        + [b"OK (dimmer set)\r\n"]  # set_dimmer(255)
        + [b"OK (dimmer set)\r\n"] * 10  # shutdown + extras
        + [b""] * 50
    )
    mb.ser = ser
    return mb


@pytest.fixture
def gm(tmp_path, mock_mb):
    """
    GeneralExperimentMethod with:
      - a 3-row method CSV  (set_dimmer / status / set_dimmer)
      - InstrumentManager patched to inject mock_mb
      - all output files directed to tmp_path
    """
    method_csv = tmp_path / "method.csv"
    method_csv.write_text(
        "Component,Action,Parameters,Notes,delay\n"
        "MirrorBox365nm_1,set_dimmer,value=200,,0.0\n"
        "MirrorBox365nm_1,status,,,0.0\n"
        "MirrorBox365nm_1,set_dimmer,value=255,,0.0\n"
    )

    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text("InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n")

    def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
        self_im.instrument_config_file = instrument_config_file
        self_im.experiment_subdir = experiment_subdir
        self_im.instruments = {"MirrorBox365nm_1": mock_mb}
        self_im.instrument_types = {"MirrorBox365nm_1": "MirrorBox365nm"}
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
    """Run experiment with StatusMonitor patched out, return the log CSV as a DataFrame."""
    with patch(_SM_START):
        gm.run_experiment()
    return pd.read_csv(gm.logger.log_filename)


# ---------------------------------------------------------------------------
# Routing — does run_experiment() reach execute_mirror_box()?
# ---------------------------------------------------------------------------


class TestRouting:

    def test_set_dimmer_action_is_logged(self, gm):
        log = _run(gm)
        mb_rows = log[log["Component"] == "MirrorBox365nm_1"]
        assert "set_dimmer" in mb_rows["Action"].values

    def test_status_action_is_logged(self, gm):
        log = _run(gm)
        mb_rows = log[log["Component"] == "MirrorBox365nm_1"]
        assert "status" in mb_rows["Action"].values

    def test_no_device_not_found_errors(self, gm):
        """MirrorBox365nm_1 must always be found in instruments."""
        log = _run(gm)
        not_found = log[log["Output"].str.contains("not found", na=False)]
        assert len(not_found) == 0

    def test_all_three_actions_logged(self, gm):
        log = _run(gm)
        mb_rows = log[log["Component"] == "MirrorBox365nm_1"]
        assert len(mb_rows) >= 3


# ---------------------------------------------------------------------------
# Serial commands — correct bytes reach the mock device
# ---------------------------------------------------------------------------


class TestSerialCommands:

    def test_set_dimmer_200_sent_to_device(self, gm, mock_mb):
        ser = mock_mb.ser  # capture before run — close() sets mb.ser = None
        _run(gm)
        written = [c.args[0] for c in ser.write.call_args_list]
        assert b"dim 200\n" in written, f"Expected dim 200 in {written}"

    def test_set_dimmer_255_sent_to_device(self, gm, mock_mb):
        ser = mock_mb.ser
        _run(gm)
        written = [c.args[0] for c in ser.write.call_args_list]
        assert b"dim 255\n" in written, f"Expected dim 255 in {written}"

    def test_status_command_sent_to_device(self, gm, mock_mb):
        ser = mock_mb.ser
        _run(gm)
        written = [c.args[0] for c in ser.write.call_args_list]
        assert b"s\n" in written, f"Expected status command in {written}"

    def test_shutdown_dims_to_255(self, gm, mock_mb):
        """Shutdown policy must call set_dimmer(255) regardless of experiment actions."""
        ser = mock_mb.ser
        _run(gm)
        written = [c.args[0] for c in ser.write.call_args_list]
        # dim 255 must appear at least twice: once in method CSV, once from shutdown
        assert (
            written.count(b"dim 255\n") >= 2
        ), f"Expected at least 2 x dim 255 (method + shutdown), got: {written}"


# ---------------------------------------------------------------------------
# Log output — correct values written to CSV
# ---------------------------------------------------------------------------


class TestLogOutput:

    def test_status_output_contains_dict_keys(self, gm):
        log = _run(gm)
        status_row = log[
            (log["Component"] == "MirrorBox365nm_1") & (log["Action"] == "status")
        ]
        assert len(status_row) > 0
        output = status_row["Output"].iloc[0]
        assert "light1_on" in output
        assert "temp_light1_c" in output

    def test_set_dimmer_output_contains_ok(self, gm):
        log = _run(gm)
        dim_rows = log[
            (log["Component"] == "MirrorBox365nm_1") & (log["Action"] == "set_dimmer")
        ]
        assert len(dim_rows) > 0
        assert dim_rows["Output"].str.contains("OK").any()

    def test_shutdown_logged_in_csv(self, gm):
        log = _run(gm)
        shutdown_row = log[
            (log["Component"] == "MirrorBox365nm_1")
            & (log["Action"] == "shutdown")
        ]
        assert len(shutdown_row) > 0


# ---------------------------------------------------------------------------
# Error handling — unknown actions logged, not silently swallowed
# ---------------------------------------------------------------------------


class TestErrorHandling:

    def test_unknown_action_logged_as_error(self, tmp_path, mock_mb):
        """An unrecognised action must appear in the log as an Error, not crash silently."""
        method_csv = tmp_path / "bad_method.csv"
        method_csv.write_text(
            "Component,Action,Parameters,Notes,delay\n"
            "MirrorBox365nm_1,nonexistent_action,,,0.0\n"
        )
        config_csv = tmp_path / "instruments.csv"
        config_csv.write_text("InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n")

        def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
            self_im.instrument_config_file = instrument_config_file
            self_im.experiment_subdir = experiment_subdir
            self_im.instruments = {"MirrorBox365nm_1": mock_mb}
            self_im.instrument_types = {"MirrorBox365nm_1": "MirrorBox365nm"}
            self_im.instrument_config = None

        mock_mb.ser.readline.side_effect = [b""] * 50

        with patch(_IM_INIT, _fake_im_init):
            bad_gm = GeneralExperimentMethod(
                input_file=str(method_csv),
                instrument_config_file=str(config_csv),
                output_dir=str(tmp_path / "output"),
                instrument_control_file=str(tmp_path / "instrument_control.txt"),
                dh2000_light_source_control_file=str(tmp_path / "dh2000_control.txt"),
            )

        with patch(_SM_START):
            bad_gm.run_experiment()

        log = pd.read_csv(bad_gm.logger.log_filename)
        error_rows = log[log["Output"].str.contains("Error", na=False)]
        assert len(error_rows) > 0, "Expected at least one Error row in the log"


# ---------------------------------------------------------------------------
# DeviceExecutor unit — test execute_mirror_box in isolation
# ---------------------------------------------------------------------------


class TestExecuteMirrorBox:
    """
    Tests DeviceExecutor.execute_mirror_box() directly, bypassing
    GeneralExperimentMethod entirely.
    """

    @pytest.fixture
    def executor(self, tmp_path):
        log_path = tmp_path / "log.csv"
        log_path.write_text("Time,Component,Action,Parameters,Output,Notes\n")
        logged = []

        def _log(component, action, params, output, notes=""):
            logged.append(
                {
                    "component": component,
                    "action": action,
                    "params": params,
                    "output": str(output),
                }
            )

        ex = DeviceExecutor(
            bed_layouts={},
            log_callback=_log,
            start_time=datetime.now(),
            continue_flag_getter=lambda: True,
        )
        ex._logged = logged
        return ex

    def test_set_dimmer_calls_device(self, executor, mock_mb):
        mock_mb.ser.readline.side_effect = [b"OK (dimmer set)\r\n"] + [b""] * 10
        executor.execute_mirror_box(
            "set_dimmer", "value=128", "MirrorBox365nm_1", mock_mb
        )
        mock_mb.ser.write.assert_called_with(b"dim 128\n")

    def test_status_logged(self, executor, mock_mb):
        mock_mb.ser.readline.side_effect = [
            b"Light1: ON | Light2: ON | DimmerPWM: 255\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ] + [b""] * 10
        with patch.object(mock_mb, "drain"):
            executor.execute_mirror_box("status", "", "MirrorBox365nm_1", mock_mb)
        assert any(e["action"] == "status" for e in executor._logged)

    def test_unknown_action_raises_and_logs_error(self, executor, mock_mb):
        mock_mb.ser.readline.side_effect = [b""] * 20
        with pytest.raises(ValueError, match="Unknown PhotoReactor action"):
            executor.execute_mirror_box("bad_action", "", "MirrorBox365nm_1", mock_mb)
        assert any("Error" in e["output"] for e in executor._logged)
