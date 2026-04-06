# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and Joao Luiz Albuquerque are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

import pytest
from unittest.mock import patch, MagicMock

from devices.custom_components.photo_reactor.mirror_box_365nm.mirror_box_365nm import MirrorBox365nm
from conftest import (make_mirror_box_response, make_mirror_box_365nm_device)

# ---------------------------------------------------------------------------
# Communication Connect and Close
# ---------------------------------------------------------------------------

class TestMirrorBox365nmCommunication:

    def test_successful_initialization(self):
        """Test that the light source initializes successfully with a valid port."""
        with patch("devices.custom_components.photo_reactor.mirror_box_365nm.mirror_box_365nm.serial.Serial") as mock_serial, \
             patch("time.sleep"):
            mock_serial.return_value.in_waiting = 0
            light = MirrorBox365nm(port="COM_TEST")
            light.connect()
            assert light.ser is not None
            print("Successful initialization test passed.")

    def test_failed_initialization(self):
        """Test that the light source raises ConnectionError on a failed serial connection."""
        with patch("devices.custom_components.photo_reactor.mirror_box_365nm.mirror_box_365nm.serial.Serial",
                   side_effect=Exception("Serial connection failed")):
            light = MirrorBox365nm(port="COM_TEST")
            with pytest.raises(ConnectionError):
                light.connect()
            print("Failed initialization test passed.")

# ---------------------------------------------------------------------------
# Light source parameters
# ---------------------------------------------------------------------------

class TestMirrorBox365nmParameters:
    """Test that all parameters are initialized correctly."""

    def test_initialization(self):
        photoreactor = MirrorBox365nm(port="COM_TEST")
        assert photoreactor.port == "COM_TEST"
        assert photoreactor.baudrate == 9600
        assert photoreactor.name == "MirrorBox365nm"
        assert photoreactor.timeout == 2.0
        assert photoreactor.ser is None

        print("Parameter initialization test passed.")


# ---------------------------------------------------------------------------
# set_dimmer 
# ---------------------------------------------------------------------------

class TestMirrorBox365nmSetDimmer:
    
    @pytest.mark.parametrize("input_value, expected_command", [
        (-10, b"dim 0\n"),  # Below range, should clamp to 0
        (0, b"dim 0\n"),    # Boundary case, should be 0
        (128, b"dim 128\n"), # Mid-range value, should be unchanged
        (255, b"dim 255\n"), # Boundary case, should be 255
        (300, b"dim 255\n"), # Above range, should clamp to 255
    ])
    def test_set_dimmer_value(self, input_value, expected_command):
        """Test that set_dimmer correctly clamps values to the 0-255 range."""
        mb = make_mirror_box_365nm_device()
        mb.set_dimmer(input_value)
        mb.ser.write.assert_called_once_with(expected_command)
    
    @pytest.mark.parametrize("input_value", [
        "invalid",  # Non-integer input
        None,       # None input
        True,       # Boolean input
        [3.14],     # List input
    ])
    def test_invalid_set_dimmer_value(self, input_value):
        """Test that set_dimmer raises an error for invalid input types."""
        mb = make_mirror_box_365nm_device()
        with pytest.raises(ValueError):
            mb.set_dimmer(input_value)