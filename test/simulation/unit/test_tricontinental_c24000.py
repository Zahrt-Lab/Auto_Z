# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Luiz Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------


import pytest
from unittest.mock import patch, MagicMock

from pumps.tricontinental_c24000.tricontinental_c24000 import TricontinentalC24000
from conftest import make_tricontinental_c24000_response, make_tricontinental_c24000_device

# ---------------------------------------------------------------------------
# Communication Connect and Close
# ---------------------------------------------------------------------------

class TestTricontinentalC24000Communication:

    def test_successful_initialization(self):
        """Test that the pump initializes successfully with a valid port."""
        with patch('serial.Serial') as mock_serial, patch('time.sleep'):
            mock_serial.return_value = make_tricontinental_c24000_device()
            pump = TricontinentalC24000(port="COM_TEST")
            pump.connect()
            assert pump.serial is not None
            print("Successful initialization test passed.")

    def test_failed_initialization(self):
        """Test that the pump raises ConnectionError on a failed serial connection."""
        with patch('serial.Serial', side_effect=Exception("Serial connection failed")):
            pump = TricontinentalC24000(port="COM_TEST")
            with pytest.raises(ConnectionError):
                pump.connect()
            print("Failed initialization test passed.")

# ---------------------------------------------------------------------------
# Pump parameters
# ---------------------------------------------------------------------------

class TestTricontinentalC24000Parameters:

    def test_initialization(self):
        """Test that all parameters are initialized correctly."""
        pump = TricontinentalC24000(port="COM_TEST")
        assert pump.port == "COM_TEST"
        assert pump.baudrate == 9600
        assert pump.name == "Tricontinental_C24000"
        assert pump.serial is None
        assert pump._connected == False
        # uL_per_count: volume (µL) dispensed per one device count
        assert pump.uL_per_count == 0.005107
        assert pump.counts_per_uL == 1 / pump.uL_per_count
        assert pump.flow_rate_ul_min == 0.0
        assert pump.flow_rate_ul_sec == 0.0

        print("Parameter initialization test passed.")

# ----------------------------------------------------------------------------
# set_flow_rate
# ----------------------------------------------------------------------------

class TestSetFlowRate:

    @pytest.mark.parametrize("flow_rate", [
        (100),
        (500),
        (1000),
        (5000),
    ])
    def test_valid_flow_rate(self, flow_rate):
        """Test that setting a valid flow rate updates flow_rate_ul_min correctly."""
        pump = TricontinentalC24000(port="COM_TEST")
        pump._connected = True
        pump.serial = MagicMock()
        pump.set_flow_rate(flow_rate)
        assert pump.flow_rate_ul_min == flow_rate
        print("Valid flow rate test passed.")

    @pytest.mark.parametrize("flow_rate", [
        (0),
        (-10),
        ("invalid"),
    ])
    def test_invalid_flow_rate(self, flow_rate):
        """Test that setting an invalid flow rate raises an error."""
        pump = TricontinentalC24000(port="COM_TEST")
        pump._connected = True
        pump.serial = MagicMock()
        with pytest.raises((ValueError, TypeError)):
            pump.set_flow_rate(flow_rate)
        print(f"Invalid flow rate '{flow_rate}' test passed.")

    @pytest.mark.parametrize("flow_rate", [
        (0),
        (-1),
        ("invalid"),
    ])
    def test_invalid_flow_rate_values(self, flow_rate):
        """Test that setting invalid flow rate values raises an error."""
        pump = TricontinentalC24000(port="COM_TEST")
        pump._connected = True
        pump.serial = MagicMock()
        with pytest.raises((ValueError, TypeError)):
            pump.set_flow_rate(flow_rate)
        print(f"Invalid flow rate value '{flow_rate}' test passed.")

# ---------------------------------------------------------------------------
# Aspirate and dispense
# ---------------------------------------------------------------------------

class TestAspirateAndDispense:

    @pytest.mark.parametrize("flow_rate, volume", [
        (100, 500),
        (500, 1000),
        (1000, 2000),
        (4000, 2500),
    ])
    def test_valid_dispense_command(self, flow_rate, volume):
        """dispense(flow_rate, volume) completes without error when connected."""
        pump = TricontinentalC24000(port="COM_TEST")
        pump._connected = True
        pump.serial = MagicMock()
        pump.serial.is_open = True
        pump.serial.in_waiting = 0
        # 'o' in response → is_valve_output() returns True; ETX terminates each read_response() call
        pump.serial.read.side_effect = [b'o', b'\x03'] * 100
        # Return a tiny pump_time so the dispense timing loop exits immediately
        pump._calculate_pump_time = MagicMock(return_value=(0.001, 0.001))
        with patch('time.sleep'):
            pump.dispense(flow_rate, volume)
        print(f"Dispense with flow rate {flow_rate} and volume {volume} test passed.")

    @pytest.mark.parametrize("flow_rate, volume", [
        (100, -500),
        (-100, 1000),
        (1000, 0),
    ])
    def test_invalid_dispense_command(self, flow_rate, volume):
        """dispense() with invalid flow rate or volume should raise ValueError."""
        pump = TricontinentalC24000(port="COM_TEST")
        pump._connected = True
        pump.serial = MagicMock()
        with pytest.raises(ValueError):
            pump.dispense(flow_rate, volume)
        print(f"Dispense with invalid flow rate {flow_rate} and volume {volume} test passed.")
