"""
Unit tests for MirrorBox365nm — pure logic, no real serial hardware.

A MagicMock is attached directly to mb.ser so no COM port is opened.
Each test covers a single piece of logic in isolation.
"""

import pytest
from unittest.mock import MagicMock, patch

from custom_components.light_source.mirror_box_365nm.mirror_box_365nm import MirrorBox365nm


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_device(readline_responses: list[bytes]) -> MirrorBox365nm:
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
# set_dimmer — value clamping
# ---------------------------------------------------------------------------

class TestSetDimmerClamping:

    def test_negative_clamped_to_zero(self):
        mb = _make_device([b"OK (dimmer set)\r\n"])
        mb.set_dimmer(-10)
        mb.ser.write.assert_called_once_with(b"dim 0\n")

    def test_above_255_clamped_to_255(self):
        mb = _make_device([b"OK (dimmer set)\r\n"])
        mb.set_dimmer(300)
        mb.ser.write.assert_called_once_with(b"dim 255\n")

    def test_valid_midrange_unchanged(self):
        mb = _make_device([b"OK (dimmer set)\r\n"])
        mb.set_dimmer(128)
        mb.ser.write.assert_called_once_with(b"dim 128\n")

    def test_boundary_zero(self):
        mb = _make_device([b"OK (dimmer set)\r\n"])
        mb.set_dimmer(0)
        mb.ser.write.assert_called_once_with(b"dim 0\n")

    def test_boundary_255(self):
        mb = _make_device([b"OK (dimmer set)\r\n"])
        mb.set_dimmer(255)
        mb.ser.write.assert_called_once_with(b"dim 255\n")

    def test_returns_ok_string(self):
        mb = _make_device([b"OK (dimmer set)\r\n"])
        result = mb.set_dimmer(128)
        assert "OK" in result


# ---------------------------------------------------------------------------
# _read_response — CSV stream line filtering
# ---------------------------------------------------------------------------

class TestReadResponseFilter:

    def test_skips_csv_stream_line_returns_next(self):
        """A temperature CSV line should be skipped; the following line returned."""
        mb = _make_device([
            b"26.41,26.41\r\n",      # stream line — must be skipped
            b"OK (dimmer set)\r\n",  # real response — must be returned
        ])
        assert mb._read_response() == "OK (dimmer set)"

    def test_returns_non_csv_immediately(self):
        mb = _make_device([b"OK (dimmer set)\r\n"])
        assert mb._read_response() == "OK (dimmer set)"

    def test_returns_empty_string_when_no_response(self):
        mb = _make_device([b""] * 20)
        assert mb._read_response() == ""

    def test_skips_multiple_consecutive_csv_lines(self):
        mb = _make_device([
            b"26.41,26.41\r\n",
            b"26.50,26.55\r\n",
            b"OK (dimmer set)\r\n",
        ])
        assert mb._read_response() == "OK (dimmer set)"

    def test_non_float_csv_not_filtered(self):
        """A line with a comma but non-float content must NOT be treated as a stream line."""
        mb = _make_device([b"Light1: ON,extra\r\n"])
        assert mb._read_response() == "Light1: ON,extra"


# ---------------------------------------------------------------------------
# status() — response parsing
# ---------------------------------------------------------------------------

class TestStatusParsing:

    def _run_status(self, responses: list[bytes]) -> dict:
        """Run status() with given mock readline responses, drain patched out."""
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
        expected = {
            "light1_on", "light2_on", "dimmer_pwm",
            "temp_light1_c", "temp_light2_c",
            "raw_line1", "raw_line2",
        }
        assert set(result.keys()) == expected

    def test_csv_stream_line_skipped_before_response(self):
        """A stream line buffered before the status response must be transparently skipped."""
        result = self._run_status([
            b"26.41,26.41\r\n",                               # stream — skip
            b"Light1: ON | Light2: ON | DimmerPWM: 255\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ])
        assert result["light1_on"] is True
        assert result["temp_light1_c"] == pytest.approx(45.30)

    def test_garbled_line1_returns_none_not_crash(self):
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
# read_temperature_stream — stream CSV parsing
# ---------------------------------------------------------------------------

class TestReadTemperatureStream:

    def test_parses_temp_light1_and_light2(self):
        mb = _make_device([b"45.30,44.80\r\n"])
        result = mb.read_temperature_stream()
        assert result["temp_light1_c"] == pytest.approx(45.30)
        assert result["temp_light2_c"] == pytest.approx(44.80)

    def test_skips_non_csv_lines_before_data(self):
        mb = _make_device([
            b"TC3_light1,TC4_light2\r\n",  # header line on startup — skip
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
