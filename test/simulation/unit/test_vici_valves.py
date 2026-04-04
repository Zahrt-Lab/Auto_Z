# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Unit tests for VICI selector valves — pure logic, no real serial hardware.
A MagicMock is attached directly to valve.ser; GeneralExperimentMethod is never involved.
"""

import pytest
import serial
from unittest.mock import patch, MagicMock

from devices.industry_components.valves.vici_valves.vici_valves import ViciValve
from conftest import make_vici_valve_response, make_vici_valve_device

# ---------------------------------------------------------------------------
# Communication Connect and Close
# ---------------------------------------------------------------------------


class TestViciValveCommunication:

    def test_successful_initialization(self):
        """Test that the valve initializes successfully with a valid port."""
        with patch("serial.Serial") as mock_serial:
            mock_serial.return_value = make_vici_valve_device()
            valve = ViciValve(port="COM_TEST", valve_type="6-way")
            assert valve.ser is not None
            assert valve.positions == 6
            print("Successful initialization test passed.")

    def test_failed_initialization(self):
        """Test that the valve raises SerialException on a failed serial connection."""
        with patch(
            "serial.Serial",
            side_effect=serial.SerialException("Serial connection failed"),
        ):
            with pytest.raises(serial.SerialException):
                ViciValve(port="COM_TEST", valve_type="6-way")
            print("Failed initialization test passed.")


# ---------------------------------------------------------------------------
# Valve parameters
# ---------------------------------------------------------------------------


class TestViciValveParameters:

    @pytest.mark.parametrize(
        "valve_type, expected_positions",
        [
            ("6-way", 6),
            ("10-way", 10),
            ("24-way", 24),
        ],
    )
    def test_valid_initialization(self, valve_type, expected_positions):
        """Test that preset valve types set the correct number of positions."""
        with patch("serial.Serial") as mock_serial:
            mock_serial.return_value = make_vici_valve_device()
            valve = ViciValve(port="COM_TEST", valve_type=valve_type)
            assert valve.positions == expected_positions
            print(f"Valid initialization for {valve_type} test passed.")

    @pytest.mark.parametrize(
        "valve_type",
        [
            "5-way",
            "invalid",
            "100000-way",
        ],
    )
    def test_invalid_initialization(self, valve_type):
        """Test that unknown valve types raise ValueError before opening serial."""
        with pytest.raises(ValueError):
            ViciValve(port="COM_TEST", valve_type=valve_type)
        print(f"Invalid initialization for '{valve_type}' test passed.")

    def test_set_number_of_positions_sends_correct_command(self):
        """Test that set_number_of_positions sends the right NP command."""
        with patch("serial.Serial") as mock_serial:
            mock_serial.return_value = make_vici_valve_device()
            valve = ViciValve(port="COM_TEST", valve_type="6-way")
        valve.ser.write.reset_mock()  # clear writes from __init__
        valve.set_number_of_positions(10)
        valve.ser.write.assert_called_once_with(b"NP10\r")
        print("set_number_of_positions command test passed.")

    @pytest.mark.parametrize("n", [5, 0, 42, -2])
    def test_set_number_of_positions_invalid(self, n):
        """Test that odd or out-of-range position counts raise ValueError."""
        with patch("serial.Serial") as mock_serial:
            mock_serial.return_value = make_vici_valve_device()
            valve = ViciValve(port="COM_TEST", valve_type="6-way")
        with pytest.raises(ValueError):
            valve.set_number_of_positions(n)
        print(f"Invalid position count {n} test passed.")

    def test_check_firmware_version_sends_command(self):
        """Test that check_firmware_version sends 'VR' and returns the decoded response."""
        with patch("serial.Serial") as mock_serial:
            mock_serial.return_value = make_vici_valve_device()
            valve = ViciValve(port="COM_TEST", valve_type="6-way")
        valve.ser.readline.return_value = b"V1.2.3\r\n"
        valve.ser.write.reset_mock()
        result = valve.check_firmware_version()
        assert result == "V1.2.3"
        valve.ser.write.assert_called_once_with(b"VR\r")
        print("check_firmware_version test passed.")


# ---------------------------------------------------------------------------
# Go To Position
# ---------------------------------------------------------------------------


class TestGoToPosition:

    @pytest.mark.parametrize("position", [1, 3, 6])
    def test_valid_position(self, position):
        """Test that go_to_position sends the correct GO command."""
        with patch("serial.Serial") as mock_serial:
            mock_serial.return_value = make_vici_valve_device()
            valve = ViciValve(port="COM_TEST", valve_type="6-way")
        valve.ser.write.reset_mock()  # clear writes from __init__
        valve.go_to_position(position)
        valve.ser.write.assert_called_once_with(f"GO{position:02}\r".encode())
        print(f"Valid position {position} test passed.")

    @pytest.mark.parametrize("position", [0, 7, "invalid"])
    def test_invalid_position(self, position):
        """Test that out-of-range or non-integer positions raise an error."""
        with patch("serial.Serial") as mock_serial:
            mock_serial.return_value = make_vici_valve_device()
            valve = ViciValve(port="COM_TEST", valve_type="6-way")
        # 0 and 7 raise ValueError (out of range); "invalid" raises TypeError (comparison)
        with pytest.raises((ValueError, TypeError)):
            valve.go_to_position(position)
        print(f"Invalid position '{position}' test passed.")
