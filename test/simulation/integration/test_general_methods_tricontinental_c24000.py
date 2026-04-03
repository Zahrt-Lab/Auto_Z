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
from unittest.mock import MagicMock, patch

from methods.methods import GeneralExperimentMethod
from conftest import make_tricontinental_c24000_response

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_c24000():
    """Tricontinental C24000 with mock serial, pre-loaded with enough read() responses."""
    from pumps.tricontinental_c24000.tricontinental_c24000 import TricontinentalC24000
    pump = TricontinentalC24000(port="COM_TEST")
    ser = MagicMock()
    ser.is_open = True
    ser.read.side_effect = [make_tricontinental_c24000_response(25.0)] * 5 + [b''] * 10
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
    
# ---------------------------------------------------------------------------
# Routing - does run_experiment() successfully run the right tricontinental methods?
# ---------------------------------------------------------------------------

class TestRouting:

    def test_aspirate_and_dispense_appear_in_logic(self, gm):
        log = run(gm)
        tricontinental_c24000 = log[log["Component"] == "C24000_1"]
        assert set(tricontinental_c24000["Action"]) == {"aspirate", "dispense"}

    def test_no_device_not_found_errors(self, gm):
        log = run(gm)
        assert log["Output"].str.contains("not found").sum() == 0

# ---------------------------------------------------------------------------
# Log output - correct values written to the CSV log?
# ---------------------------------------------------------------------------

class TestLogOutput:

    @pytest.mark.parametrize("flow_rate", [
        (100.0),
        (0.1),
        (5000.0),
    ])
    def test_dispense_logged_with_valid_flow_rate(self, gm):
        log = _run(gm)
        row = log[(log["Component"] == "C24000_1") & (log["Action"] == "dispense")]
        assert row["Output"].str.contains("Flow rate set to 100.0 uL/min").any()
    
    @pytest.mark.parametrize("flow_rate", [
        (0),
        (-10),
        ("invalid"),
    ])
    def test_dispense_logged_with_valid_volume(self, gm):
        log = _run(gm)
        row = log[(log["Component"] == "C24000_1") & (log["Action"] == "dispense")]
        assert row["Output"].str.contains("Volume dispensed: 100.0 uL").any()
    
    @pytest.mark.parametrize("flow_rate", [
        (0),
        (-10),
        ("invalid"),
    ])
    def test_dispense_logged_with_invalide_flow_rate(self, gm):
        log = _run(gm)
        row = log[(log["Component"] == "C24000_1") & (log["Action"] == "dispense")]
        assert row["Output"].str.contains("Invalid flow rate").any()
    
    def test_dispense_logged_with_invalid_volume(self, gm):
        log = _run(gm)
        row = log[(log["Component"] == "C24000_1") & (log["Action"] == "dispense")]
        assert row["Output"].str.contains("Invalid volume").any()

# ---------------------------------------------------------------------------
# Error handling