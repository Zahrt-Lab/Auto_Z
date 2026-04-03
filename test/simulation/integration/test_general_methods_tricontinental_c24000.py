# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

'''
Integration tests for tricontinental c24000 pump through GeneralExperimentMethod.

Every test goes through the run_experiment() no direct C24000 method calls.
InstrumentManager is patched to inject a C24000 with mocked serial.
'''

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from methods.methods import GeneralExperimentMethod
from conftest import make_tricontinental_c24000_response

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_c24000():
    """Tricontinental C24000 with mock serial, pre-loaded with enough read() responses."""
    from devices.industry_components.pumps.tricontinental_c24000.tricontinental_c24000 import TricontinentalC24000
    pump = TricontinentalC24000(port="COM_TEST")
    ser = MagicMock()
    ser.is_open = True
    ser.read.side_effect = [make_tricontinental_c24000_response("25.0")] * 5 + [b''] * 10
    pump.serial = ser
    pump._connected = True
    return pump

def _build_gm(tmp_path, mock_c24000, method_rows: str) -> GeneralExperimentMethod:
    """Create a GeneralExperimentMethod with InstrumentManager patched to inject mock_c24000."""
    method_csv = tmp_path / "method.csv"
    method_csv.write_text(
        "Component,Action,Parameters,Notes,delay\n" + method_rows
    )
    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text("InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n")

    def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
        self_im.instrument_config_file = instrument_config_file
        self_im.experiment_subdir = experiment_subdir
        self_im.instruments = {"C24000_1": mock_c24000}
        self_im.instrument_types = {"C24000_1": "Pump"}
        self_im.instrument_config = None

    with patch("methods.instrument_manager.InstrumentManager.__init__", _fake_im_init):
        return GeneralExperimentMethod(
            input_file=str(method_csv),
            instrument_config_file=str(config_csv),
            output_dir=str(tmp_path / "output"),
            instrument_control_file=str(tmp_path / "instrument_control.txt"),
            dh2000_light_source_control_file=str(tmp_path / "dh2000_control.txt"),
        )

# Adds a default flow_rate for every test
@pytest.fixture
def flow_rate():
    return 100.0

# Adds a default volume for every test
@pytest.fixture
def volume():
    return 100.0

@pytest.fixture
def gm(tmp_path, mock_c24000, flow_rate, volume):
    return _build_gm(tmp_path, mock_c24000, f'C24000_1,dispense,"flow_rate={flow_rate},volume={volume}",,0.5\n')

def _run(gm: GeneralExperimentMethod) -> pd.DataFrame:
    """Run the experiment and return the log as a DataFrame."""
    with patch("methods.status_monitor.StatusMonitor.start"), patch("time.sleep"):
        gm.run_experiment()
    return pd.read_csv(gm.log_filename)

# ---------------------------------------------------------------------------
# Log output 
# ---------------------------------------------------------------------------

class TestLogOutput:

    @pytest.mark.parametrize("flow_rate", [
        (100.0),
        (0.1),
        (5000.0),
    ])
    def test_dispense_logged_with_valid_flow_rate(self, gm, flow_rate, volume):
        log = _run(gm)
        row = log[(log["Component"] == "C24000_1") & 
                  (log["Action"] == "dispense") &
                  (log["Parameters"] == f"flow_rate={flow_rate},volume={volume}")]
        assert row["Output"].str.contains("Started async dispense", na=False).any()
    
    @pytest.mark.parametrize("volume", [
        (50.0),
        (100.0),
        (500.0),
    ])
    def test_dispense_logged_with_valid_volume(self, gm, flow_rate, volume):
        log = _run(gm)
        row = log[(log["Component"] == "C24000_1") & 
                  (log["Action"] == "dispense") & 
                  (log["Parameters"] == f"flow_rate={flow_rate},volume={volume}")]
        assert row["Output"].str.contains("Started async dispense", na=False).any()
    
    @pytest.mark.parametrize("flow_rate", [
        (0),
        (-10),
        ("invalid"),
    ])
    def test_dispense_logged_with_invalid_flow_rate(self, gm, flow_rate, volume):
        log = _run(gm)
        row = log[(log["Component"] == "C24000_1") & 
                  (log["Action"] == "dispense") &
                  (log["Parameters"] == f"flow_rate={flow_rate},volume={volume}")]
        assert log["Output"].str.contains("skipped|FAILED", na=False).any()
    
    @pytest.mark.parametrize("volume", [
        (0),
        (-100),
        ("invalid"),
    ])
    def test_dispense_logged_with_invalid_volume(self, gm, flow_rate, volume):
        log = _run(gm)
        row = log[(log["Component"] == "C24000_1") & 
                  (log["Action"] == "dispense") &
                  (log["Parameters"] == f"flow_rate={flow_rate},volume={volume}")]
        assert log["Output"].str.contains("skipped|FAILED", na=False).any()

# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:

    def test_unknown_action_logged_as_error(self, tmp_path, mock_c24000):
        bad_gm = _build_gm(tmp_path, mock_c24000, "C24000_1,nonexistent_action,,,0.5\n")
        with patch("methods.status_monitor.StatusMonitor.start"), patch("time.sleep"):
            bad_gm.run_experiment()
        log = pd.read_csv(bad_gm.log_filename)
        assert log["Output"].str.contains("Error|FAILED", na=False).any()