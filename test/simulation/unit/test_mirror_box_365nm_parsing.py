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

# TODO: This is too much code for a simple test, need to simplify this device code. 

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


# ---------------------------------------------------------------------------
# Local helper for status / temperature stream tests
# ---------------------------------------------------------------------------

def _make_device(readline_responses: list) -> MirrorBox365nm:
    """
    Return a MirrorBox365nm with a mock serial port pre-loaded with responses.
    Pads with empty bytes so readline() never raises StopIteration.
    """
    mb = MirrorBox365nm(port="COM_TEST")
    mock_ser = MagicMock()
    mock_ser.timeout = 2.0
    mock_ser.in_waiting = 0
    mock_ser.readline.side_effect = readline_responses + [b""] * 20
    mb.ser = mock_ser
    return mb


# ---------------------------------------------------------------------------
# status() 
# ---------------------------------------------------------------------------

class TestStatusParsing:

    def _run_status(self, responses: list) -> dict:
        """Run status() with drain() patched out, returning the parsed dict."""
        mb = _make_device(responses)
        with patch.object(mb, "drain"):
            return mb.status()

    def test_light1_on(self):
        result = self._run_status([
            b"Light1: ON | Light2: ON | DimmerPWM: 255\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ])
        assert result["light1_on"] is True

    def test_light1_off(self):
        result = self._run_status([
            b"Light1: OFF | Light2: ON | DimmerPWM: 255\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ])
        assert result["light1_on"] is False

    def test_light2_on(self):
        result = self._run_status([
            b"Light1: ON | Light2: ON | DimmerPWM: 255\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ])
        assert result["light2_on"] is True

    def test_light2_off(self):
        result = self._run_status([
            b"Light1: ON | Light2: OFF | DimmerPWM: 255\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ])
        assert result["light2_on"] is False

    def test_dimmer_pwm_value(self):
        result = self._run_status([
            b"Light1: ON | Light2: ON | DimmerPWM: 200\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ])
        assert result["dimmer_pwm"] == 200

    def test_temp_light1_c(self):
        result = self._run_status([
            b"Light1: ON | Light2: ON | DimmerPWM: 255\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ])
        assert result["temp_light1_c"] == pytest.approx(45.30)

    def test_temp_light2_c(self):
        result = self._run_status([
            b"Light1: ON | Light2: ON | DimmerPWM: 255\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ])
        assert result["temp_light2_c"] == pytest.approx(44.80)

    def test_all_expected_keys_present(self):
        result = self._run_status([
            b"Light1: ON | Light2: ON | DimmerPWM: 255\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ])
        assert set(result.keys()) == {
            "light1_on", "light2_on", "dimmer_pwm",
            "temp_light1_c", "temp_light2_c",
            "raw_line1", "raw_line2",
        }

    def test_csv_stream_line_skipped_before_response(self):
        """A temperature stream line buffered before the status response must be skipped."""
        result = self._run_status([
            b"26.41,26.41\r\n",
            b"Light1: ON | Light2: ON | DimmerPWM: 255\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ])
        assert result["light1_on"] is True
        assert result["temp_light1_c"] == pytest.approx(45.30)

    def test_garbled_line1_returns_none_fields(self):
        """Unparseable status line should return None fields, not raise."""
        result = self._run_status([
            b"garbage data here\r\n",
            b"more garbage\r\n",
        ])
        assert result["light1_on"] is None
        assert result["dimmer_pwm"] is None

    def test_garbled_temp_line_returns_none_temps(self):
        result = self._run_status([
            b"Light1: ON | Light2: ON | DimmerPWM: 255\r\n",
            b"not a temp line\r\n",
        ])
        assert result["temp_light1_c"] is None
        assert result["temp_light2_c"] is None


# ---------------------------------------------------------------------------
# read_temperature_stream
# ---------------------------------------------------------------------------

class TestReadTemperatureStream:

    def test_parses_temp_light1_and_light2(self):
        mb = _make_device([b"45.30,44.80\r\n"])
        result = mb.read_temperature_stream()
        assert result["temp_light1_c"] == pytest.approx(45.30)
        assert result["temp_light2_c"] == pytest.approx(44.80)

    def test_skips_non_csv_lines_before_data(self):
        """Header line on startup must be skipped; first valid CSV line returned."""
        mb = _make_device([
            b"TC3_light1,TC4_light2\r\n",
            b"45.30,44.80\r\n",
        ])
        result = mb.read_temperature_stream()
        assert result["temp_light1_c"] == pytest.approx(45.30)

    def test_returns_error_dict_when_no_data(self):
        mb = _make_device([b""] * 15)
        result = mb.read_temperature_stream()
        assert "error" in result

    def test_no_legacy_tc1_tc2_keys(self):
        """TC1/TC2 keys (temp_cold, temp_hot) must not appear in the result."""
        mb = _make_device([b"45.30,44.80\r\n"])
        result = mb.read_temperature_stream()
        assert "temp_cold" not in result
        assert "temp_hot" not in result

    def test_raw_key_present_on_success(self):
        mb = _make_device([b"45.30,44.80\r\n"])
        result = mb.read_temperature_stream()
        assert "raw" in result
        assert result["raw"] == "45.30,44.80"

    def test_timeout_is_restored_after_call(self):
        """ser.timeout must be reset to its original value after the call."""
        mb = _make_device([b"45.30,44.80\r\n"])
        mb.ser.timeout = 2.0
        mb.read_temperature_stream(timeout=0.5)
        assert mb.ser.timeout == 2.0