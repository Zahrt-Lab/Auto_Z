"""
Unit tests for TC720 temperature controller — pure logic, no real serial hardware.
A MagicMock is attached directly to tc.ser; GeneralExperimentMethod is never involved.
"""

import pytest
from unittest.mock import patch

from devices.industry_components.temperature_controller.tc720.tc720 import TC720
from conftest import make_tc720_response, make_tc720_device

_SLEEP_PATH = "devices.industry_components.temperature_controller.tc720.tc720.time.sleep"


# ---------------------------------------------------------------------------
# calculate_checksum
# ---------------------------------------------------------------------------

class TestCalculateChecksum:

    def test_correct_value(self):
        """25°C bstc list: chars sum=404 → checksum='94' → full string '*1c09c494\\r'."""
        tc = TC720(port="COM_TEST")
        result = tc.calculate_checksum(['*', '1', 'c', '0', '9', 'c', '4', 'XX', 'XX', '\r'])
        assert ''.join(result) == '*1c09c494\r'

    def test_output_format(self):
        """Result must be a 10-element list starting with '*' and ending with CR."""
        tc = TC720(port="COM_TEST")
        result = tc.calculate_checksum(['*', '0', '1', '0', '0', '0', '0', 'XX', 'XX', '\r'])
        assert len(result) == 10
        assert result[0] == '*'
        assert result[-1] == '\r'


# ---------------------------------------------------------------------------
# convert_temp_to_bstc
# ---------------------------------------------------------------------------

class TestConvertTempToBstc:

    @pytest.mark.parametrize("temp,fragment", [
        (25.0,  '*1c09c494\r'),  # 2500 → 0x09c4, full command
        (0.0,   '0000'),         # 0    → 0x0000
        (100.0, '2710'),         # 10000 → 0x2710
        (37.5,  '0ea6'),         # 3750  → 0x0ea6
    ])
    def test_correct_encoding(self, temp, fragment):
        tc = TC720(port="COM_TEST")
        assert fragment in ''.join(tc.convert_temp_to_bstc(temp))

    def test_output_format(self):
        """Result must be a list starting with '*' and ending with CR."""
        tc = TC720(port="COM_TEST")
        result = tc.convert_temp_to_bstc(25.0)
        assert isinstance(result, list)
        assert result[0] == '*'
        assert result[-1] == '\r'


# ---------------------------------------------------------------------------
# _build_query
# ---------------------------------------------------------------------------

class TestBuildQuery:

    @pytest.mark.parametrize("sensor_code,expected", [
        ('01', '*01000021\r'),
        ('04', '*04000024\r'),
    ])
    def test_query_command(self, sensor_code, expected):
        tc = TC720(port="COM_TEST")
        assert ''.join(tc._build_query(sensor_code)) == expected


# ---------------------------------------------------------------------------
# set_temperature
# ---------------------------------------------------------------------------

class TestSetTemperature:

    @pytest.mark.parametrize("temp", [-0.1, 100.1, -50.0, 200.0])
    def test_out_of_range_raises_value_error(self, temp):
        tc = make_tc720_device([])
        with pytest.raises(ValueError, match="0°C and 100°C"):
            tc.set_temperature(temp)

    @pytest.mark.parametrize("temp", [0.0, 25.0, 100.0])
    def test_valid_range_does_not_raise(self, temp):
        make_tc720_device([]).set_temperature(temp)  # must not raise

    def test_sends_correct_bytes_and_flushes(self):
        """25°C must produce b'*1c09c494\\r' followed by a flush."""
        tc = make_tc720_device([])
        tc.set_temperature(25.0)
        tc.ser.write.assert_called_once_with(b'*1c09c494\r')
        tc.ser.flush.assert_called_once()

    def test_not_connected_raises_runtime_error(self):
        tc = TC720(port="COM_TEST")
        tc.ser = None
        with pytest.raises(RuntimeError, match="not connected"):
            tc.set_temperature(25.0)


# ---------------------------------------------------------------------------
# get_temperature
# ---------------------------------------------------------------------------

class TestGetTemperature:

    @pytest.mark.parametrize("temp", [25.0, 37.5, 0.0, -5.0])
    def test_round_trip(self, temp):
        """Encoded response must decode back to the original temperature."""
        tc = make_tc720_device([make_tc720_response(temp)])
        with patch(_SLEEP_PATH):
            assert tc.get_temperature() == pytest.approx(temp)

    @pytest.mark.parametrize("bad_response,match", [
        (b'*09c4',       "Unexpected response"),  # too short
        (b'X09c49400',   "Unexpected response"),  # no leading '*'
        (b'*XXXX0000',   "placeholder"),           # device not ready
    ])
    def test_bad_response_raises_ioerror(self, bad_response, match):
        tc = make_tc720_device([bad_response])
        with patch(_SLEEP_PATH):
            with pytest.raises(IOError, match=match):
                tc.get_temperature()

    def test_checksum_mismatch_raises_ioerror(self):
        valid = make_tc720_response(25.0)
        corrupt = valid[:5] + b'ZZ' + valid[7:]
        tc = make_tc720_device([corrupt])
        with patch(_SLEEP_PATH):
            with pytest.raises(IOError, match="Checksum mismatch"):
                tc.get_temperature()

    def test_sensor2_sends_sensor2_query(self):
        tc = make_tc720_device([make_tc720_response(30.0)])
        with patch(_SLEEP_PATH):
            tc.get_temperature(sensor=2)
        assert b'04' in tc.ser.write.call_args[0][0]


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

class TestStatus:

    def test_disconnected_returns_error(self):
        tc = TC720(port="COM_TEST")
        tc._connected = False
        result = tc.status()
        assert result["ok"] is False
        assert result["code"] == "disconnected"

    def test_connected_returns_temperature(self):
        tc = make_tc720_device([make_tc720_response(37.5)])
        with patch(_SLEEP_PATH):
            result = tc.status()
        assert result["ok"] is True
        assert result["code"] == "ok"
        assert result["temperature_c"] == pytest.approx(37.5)

    def test_bad_response_returns_no_response(self):
        tc = make_tc720_device([b'*XXXX0000'])
        with patch(_SLEEP_PATH):
            result = tc.status()
        assert result["ok"] is False
        assert result["code"] == "no_response"
