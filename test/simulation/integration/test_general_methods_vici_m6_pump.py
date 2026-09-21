# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Andrew Zahrt
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
Integration tests for tricontinental c24000 pump through GeneralExperimentMethod.

Every test goes through the run_experiment() no direct VICI M6 pump method calls.
InstrumentManager is patched to inject a VICI_M6_Pumps with mocked serial.
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from methods.methods import GeneralExperimentMethod
from conftest import make_vici_m6_response

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_vici_m6():
    """VICI M6 pump with mock serial, pre-loaded with enough read() responses."""
    from devices.industry_components.pumps.vici_m6_pump.vici_m6_pump import (
        VICI_M6_Pumps,
    )

    pump = VICI_M6_Pumps(port="COM_TEST")
    ser = MagicMock()
    ser.is_open = True
    ser.read.side_effect = [make_vici_m6_response("25.0")] * 5 + [b""] * 10
    pump.ser = ser
    pump._connected = True
    return pump


# TODO : A lot of this code is very similar to the tricontinental c24000 integration test,
# once test code is up and running, consider refactoring into a shared helper function
def _build_gm(tmp_path, mock_vici_m6, method_rows: str) -> GeneralExperimentMethod:
    """Create a GeneralExperimentMethod with InstrumentManager patched to inject mock_vici_m6."""
    method_csv = tmp_path / "method.csv"
    method_csv.write_text("Component,Action,Parameters,Notes,delay\n" + method_rows)
    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text("InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n")

    def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
        self_im.instrument_config_file = instrument_config_file
        self_im.experiment_subdir = experiment_subdir
        self_im.instruments = {"VICI_M6_1": mock_vici_m6}
        self_im.instrument_types = {"VICI_M6_1": "Pump"}
        self_im.instrument_config = None

    with patch("methods.instrument_manager.InstrumentManager.__init__", _fake_im_init):
        return GeneralExperimentMethod(
            input_file=str(method_csv),
            instrument_config_file=str(config_csv),
            output_dir=str(tmp_path / "output"),
            instrument_control_file=str(tmp_path / "instrument_control.txt"),
            dh2000_light_source_control_file=str(tmp_path / "dh2000_control.txt"),
        )


@pytest.fixture
def flow_rate():
    """Default flow rate for tests."""
    return 100.0


@pytest.fixture
def volume():
    """Default volume for tests."""
    return 100.0


@pytest.fixture
def gm(tmp_path, mock_vici_m6, direction, flow_rate, volume):
    return _build_gm(
        tmp_path,
        mock_vici_m6,
        f'VICI_M6_1,{direction},"flow_rate={flow_rate},volume={volume}",,0.5\n',
    )


def _run(gm: GeneralExperimentMethod) -> pd.DataFrame:
    """Run the experiment and return the log as a DataFrame."""
    with patch("methods.status_monitor.StatusMonitor.start"), patch("time.sleep"):
        gm.run_experiment()
    return pd.read_csv(gm.logger.log_filename)


# ---------------------------------------------------------------------------
# Log output
# ---------------------------------------------------------------------------


class TestLogOutput:

    @pytest.mark.parametrize(
        "direction,flow_rate",
        [
            ("dispense", 100.0),
            ("dispense", 0.1),
            ("dispense", 4000.0),
        ],
    )
    def test_dispense_logged_with_valid_flow_rate(
        self, gm, direction, flow_rate, volume
    ):
        log = _run(gm)
        row = log[
            (log["Component"] == "VICI_M6_1")
            & (log["Action"] == direction)
            & (log["Parameters"] == f"flow_rate={flow_rate},volume={volume}")
        ]
        assert row["Output"].str.contains("Started async dispense", na=False).any()

    @pytest.mark.parametrize(
        "direction,volume",
        [
            ("dispense", 50.0),
            ("dispense", 100.0),
            ("dispense", 500.0),
        ],
    )
    def test_dispense_logged_with_valid_volume(self, gm, direction, flow_rate, volume):
        log = _run(gm)
        row = log[
            (log["Component"] == "VICI_M6_1")
            & (log["Action"] == direction)
            & (log["Parameters"] == f"flow_rate={flow_rate},volume={volume}")
        ]
        assert row["Output"].str.contains("Started async dispense", na=False).any()

    @pytest.mark.parametrize(
        "direction,flow_rate",
        [
            ("dispense", 0),
            ("dispense", -10),
            ("dispense", "invalid"),
        ],
    )
    def test_dispense_logged_with_invalid_flow_rate(
        self, gm, direction, flow_rate, volume
    ):
        log = _run(gm)
        row = log[
            (log["Component"] == "VICI_M6_1")
            & (log["Action"] == direction)
            & (log["Parameters"] == f"flow_rate={flow_rate},volume={volume}")
        ]
        assert log["Output"].str.contains("skipped|FAILED", na=False).any()

    @pytest.mark.parametrize(
        "direction,volume",
        [
            ("dispense", 0),
            ("dispense", -100),
            ("dispense", "invalid"),
        ],
    )
    def test_dispense_logged_with_invalid_volume(
        self, gm, direction, flow_rate, volume
    ):
        log = _run(gm)
        row = log[
            (log["Component"] == "VICI_M6_1")
            & (log["Action"] == direction)
            & (log["Parameters"] == f"flow_rate={flow_rate},volume={volume}")
        ]
        assert log["Output"].str.contains("skipped|FAILED", na=False).any()

    @pytest.mark.parametrize(
        "direction,flow_rate",
        [("aspirate", 100.0), ("aspirate", 0.1), ("aspirate", 4000.0)],
    )
    def test_aspirtate_logged_with_valid_flow_rate(
        self, gm, direction, flow_rate, volume
    ):
        log = _run(gm)
        row = log[
            (log["Component"] == "VICI_M6_1")
            & (log["Action"] == direction)
            & (log["Parameters"] == f"flow_rate={flow_rate},volume={volume}")
        ]
        assert row["Output"].str.contains("Started async aspirate", na=False).any()

    @pytest.mark.parametrize(
        "direction,volume",
        [
            ("aspirate", 50.0),
            ("aspirate", 100.0),
            ("aspirate", 500.0),
        ],
    )
    def test_aspirate_logged_with_valid_volume(self, gm, direction, flow_rate, volume):
        log = _run(gm)
        row = log[
            (log["Component"] == "VICI_M6_1")
            & (log["Action"] == direction)
            & (log["Parameters"] == f"flow_rate={flow_rate},volume={volume}")
        ]
        assert row["Output"].str.contains("Started async aspirate", na=False).any()

    @pytest.mark.parametrize(
        "direction,flow_rate",
        [
            ("aspirate", 0),
            ("aspirate", -10),
            ("aspirate", "invalid"),
        ],
    )
    def test_aspirate_logged_with_invalid_flow_rate(
        self, gm, direction, flow_rate, volume
    ):
        log = _run(gm)
        row = log[
            (log["Component"] == "VICI_M6_1")
            & (log["Action"] == direction)
            & (log["Parameters"] == f"flow_rate={flow_rate},volume={volume}")
        ]
        assert log["Output"].str.contains("skipped|FAILED", na=False).any()

    @pytest.mark.parametrize(
        "direction,volume",
        [
            ("aspirate", 0),
            ("aspirate", -100),
            ("aspirate", "invalid"),
        ],
    )
    def test_aspirate_logged_with_invalid_volume(
        self, gm, direction, flow_rate, volume
    ):
        log = _run(gm)
        row = log[
            (log["Component"] == "VICI_M6_1")
            & (log["Action"] == direction)
            & (log["Parameters"] == f"flow_rate={flow_rate},volume={volume}")
        ]
        assert log["Output"].str.contains("skipped|FAILED", na=False).any()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:

    def test_unknown_action_logged_as_error(self, tmp_path, mock_vici_m6):
        bad_gm = _build_gm(
            tmp_path, mock_vici_m6, "VICI_M6_1,nonexistent_action,,,0.5\n"
        )
        with patch("methods.status_monitor.StatusMonitor.start"), patch("time.sleep"):
            bad_gm.run_experiment()
        log = pd.read_csv(bad_gm.logger.log_filename)
        assert log["Output"].str.contains("Error", na=False).any()
