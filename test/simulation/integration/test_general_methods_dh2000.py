"""
Integration tests for DH2000 through GeneralExperimentMethod.

Every test goes through run_experiment() — no direct DH2000 method calls.
InstrumentManager is patched to inject a DH2000LightSource with mocked serial.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from methods.methods import GeneralExperimentMethod

_IM_INIT = "methods.instrument_manager.InstrumentManager.__init__"
_SM_START = "methods.status_monitor.StatusMonitor.start"
_SLEEP = "devices.industry_components.uv_detectors.dh2000.time.sleep"
_DRAIN = "devices.industry_components.uv_detectors.dh2000.DH2000LightSource._drain"


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_dh():
    """DH2000LightSource with mock serial, pre-loaded with enough readline() responses."""
    from devices.industry_components.uv_detectors.dh2000 import DH2000LightSource

    dh = DH2000LightSource(port="COM_TEST", timeout=2.0)
    ser = MagicMock()
    ser.in_waiting = 0
    ser.readline.side_effect = (
        [b"OK\r\n"]
        + [
            b"Shutter: OPEN\r\n",
            b"Halogen: OFF\r\n",
            b"Deuterium: OFF\r\n",
        ]  # status (method row)
        + [
            b"Shutter: OPEN\r\n",
            b"Halogen: OFF\r\n",
            b"Deuterium: OFF\r\n",
        ]  # status (shutdown noop)
        + [b""] * 20
    )
    dh.ser = ser
    return dh


def _build_gm(tmp_path, mock_dh, method_rows: str) -> GeneralExperimentMethod:
    """Create a GeneralExperimentMethod with InstrumentManager patched to inject mock_dh."""
    method_csv = tmp_path / "method.csv"
    method_csv.write_text("Component,Action,Parameters,Notes,delay\n" + method_rows)
    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text("InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n")

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


@pytest.fixture
def gm(tmp_path, mock_dh):
    return _build_gm(
        tmp_path,
        mock_dh,
        "DH2000_1,shutter_open,,,0.0\n" "DH2000_1,status,,,0.0\n",
    )


def _run(gm) -> pd.DataFrame:
    """Run the experiment and return the action log as a DataFrame."""
    with patch(_SM_START), patch(_SLEEP), patch(_DRAIN):
        gm.run_experiment()
    return pd.read_csv(gm.logger.log_filename)


# ---------------------------------------------------------------------------
# Log output — correct values written to the CSV log
# ---------------------------------------------------------------------------


class TestLogOutput:

    def test_shutter_open_logs_ok(self, gm):
        log = _run(gm)
        row = log[(log["Component"] == "DH2000_1") & (log["Action"] == "shutter_open")]
        assert "OK" in row["Output"].iloc[0]

    def test_status_output_contains_dict_keys(self, gm):
        log = _run(gm)
        row = log[(log["Component"] == "DH2000_1") & (log["Action"] == "status")]
        assert "shutter_open" in row["Output"].iloc[0]


# ---------------------------------------------------------------------------
# Error handling — unknown actions logged, not silently swallowed
# ---------------------------------------------------------------------------


class TestErrorHandling:

    def test_unknown_action_logged_as_error(self, tmp_path, mock_dh):
        mock_dh.ser.readline.side_effect = [
            b"Shutter: CLOSED\r\n",
            b"Halogen: OFF\r\n",
            b"Deuterium: OFF\r\n",
        ] * 5 + [b""] * 10
        bad_gm = _build_gm(tmp_path, mock_dh, "DH2000_1,nonexistent_action,,,0.0\n")
        with patch(_SM_START), patch(_SLEEP), patch(_DRAIN):
            bad_gm.run_experiment()
        log = pd.read_csv(bad_gm.logger.log_filename)
        assert log["Output"].str.contains("Error", na=False).any()
