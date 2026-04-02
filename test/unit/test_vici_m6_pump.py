# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Unit tests for VICI M6 pump — pure logic, no real serial hardware.
A MagicMock is attached directly to tc.ser; GeneralExperimentMethod is never involved.
"""

import pytest
from unittest.mock import patch

from pumps.vici_m6_pump.vici_m6_pump import VICI_M6_Pumps
from conftest import make_vici_m6_response, make_vici_m6_device

# ---------------------------------------------------------------------------
# Communication Connect and Close
# ---------------------------------------------------------------------------

class TestViciM6PumpCommunication:

    def test_successful_initialization(self):
        """Test that the pump initializes successfully with a valid port."""
        with patch('serial.Serial') as mock_serial:
            mock_serial.return_value = make_vici_m6_device()
            pump = VICI_M6_Pumps(port="COM_TEST")
            assert pump.ser is not None
            print("Successful initialization test passed.")

    def test_failed_initialization(self):
        """Test that the pump handles failed initialization gracefully."""
        with patch('serial.Serial', side_effect=Exception("Serial connection failed")):
            pump = VICI_M6_Pumps(port="COM_TEST")
            assert pump.ser is None
            print("Failed initialization test passed.")

# ---------------------------------------------------------------------------
# Pump parameters
# ---------------------------------------------------------------------------

class TestViciM6PumpParameters:

    def test_initialization(self):
        """Test that all parameters are initialized correctly."""
        pump = VICI_M6_Pumps(port="COM_TEST")
        assert pump.MS == 256
        assert pump.P == 0
        assert pump.VI == 1000
        assert pump.VM == 76800
        assert pump.A == 1000000
        assert pump.D == 1000000
        assert pump.MA is None
        assert pump.MR is None
        assert pump.SL is None
        assert pump.SL_units == "steps/sec"

        assert pump.volume == 1000
        assert pump.volume_units == "uL"
        assert pump.flow_rate_min == 100
        assert pump.flow_rate_sec == 100 / 60
        assert pump.flow_rate_units_min == "uL/min"
        assert pump.flow_rate_units_sec == "uL/sec"

        assert pump.micro_steps == 256
        assert pump.motor_steps == 200
        assert pump.gearbox_ratio == 9.87
        assert pump.micro_steps_per_rev == 256 * 200 * 9.87
        assert pump.pump_head_volume == 99.771
        assert pump.steps_per_ul == (256 * 200 * 9.87) / 99.771
        assert pump.steps_per_ul_units == "steps/uL"
    
    def test_get_pump_parameters(self):
        """Test that pump parameters are set correctly."""
        pump = VICI_M6_Pumps(port="COM_TEST")
        assert pump.get_pump_parameters() == (f"Pump parameters:\n"
                                              f"The flow rate per minute is {pump.flow_rate_min} {pump.flow_rate_units_min}\n"
                                              f"The flow rate per second is {round(pump.flow_rate_sec,2)} {pump.flow_rate_units_sec}\n"
                                              f"The # of micro steps is  {pump.micro_steps}\n"
                                              f"The # of motor steps is  {pump.motor_steps}\n"
                                              f"The gear box ratio is  {pump.gearbox_ratio}\n"
                                              f"The number of microsteps per revolution is {round(pump.micro_steps_per_rev,2)}\n"
                                              f"The Pump Head Volume is  {pump.pump_head_volume}\n"
                                              f"The Velocity Max is {round(pump.steps_per_ul,2)} {pump.steps_per_ul_units}"
                                              )
        
#---------------------------------------------------------------------------
# set_flow_rate
#---------------------------------------------------------------------------

class TestSetFlowRate:

    @pytest.mark.parametrize("flow_rate, direction", [
        (50, "aspirating"),
        (150, "dispensing"),
        (0, "aspirating"),
        (200, "dispensing")
    ])
    def test_valid_flow_rate_and_direction(self, flow_rate, direction):
        pump = VICI_M6_Pumps(port="COM_TEST")
        pump.set_flow_rate(flow_rate, direction)
        assert pump.flow_rate_min == flow_rate
        assert pump.flow_rate_sec == flow_rate / 60.0
        assert pump.direction == direction
        print(f"Valid flow rate {flow_rate} and direction '{direction}' test passed.")

    @pytest.mark.parametrize("flow_rate, direction", [
        (50, "invalid_direction"),
        (150, ""),
        (0, None),
        (200, "123")
    ])
    def test_invalid_direction(self, flow_rate, direction):
        pump = VICI_M6_Pumps(port="COM_TEST")
        with pytest.raises(ValueError):
            pump.set_flow_rate(flow_rate, direction)
        print(f"Invalid direction '{direction}' test passed.")

    @pytest.mark.parametrize("flow_rate, direction", [
        (None, "aspirating"),
        ("50", "dispensing"),
        (5500, "aspirating"),
        (5500, "dispensing")
    ])
    def test_invalid_flow_rate(self, flow_rate, direction):
        pump = VICI_M6_Pumps(port="COM_TEST")
        with pytest.raises(ValueError):
            pump.set_flow_rate(flow_rate, direction)
        print(f"Invalid flow rate {flow_rate} test passed.")

# ----------------------------------------------------------------------------
# Aspirate and dispense
# ----------------------------------------------------------------------------

class TestAspirateAndDispense:

    def test_valid_aspirate(self):
        pump = VICI_M6_Pumps(port="COM_TEST")
        pump.set_flow_rate(100, "aspirating")
        pump.aspirate(500)
        assert pump.volume == 500
        assert pump.volume_units == "uL"
        print("Aspirate test passed.")

    def test_valid_dispense(self):
        pump = VICI_M6_Pumps(port="COM_TEST")
        pump.set_flow_rate(100, "dispensing")
        pump.dispense(500)
        assert pump.volume == 500
        assert pump.volume_units == "uL"
        print("Dispense test passed.")
    
    def test_invalid_aspirate_volume(self):
        pump = VICI_M6_Pumps(port="COM_TEST")
        pump.set_flow_rate(100, "aspirating")
        with pytest.raises(ValueError):
            pump.aspirate(-100)
        print("Invalid aspirate volume test passed.")
    
    def test_invalid_dispense_volume(self):
        pump = VICI_M6_Pumps(port="COM_TEST")
        pump.set_flow_rate(100, "dispensing")
        with pytest.raises(ValueError):
            pump.dispense(-100)
        print("Invalid dispense volume test passed.")