"""
Unit tests for TC720 temperature controller — pure logic, no real serial hardware.

A MagicMock is attached directly to tc.ser so no COM port is opened.
Each test covers a single piece of logic in isolation.
"""

import pytest
from unittest.mock import MagicMock, patch

from temperature_controller.tc720.tc720 import TC720


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SLEEP_PATH = "temperature_controller.tc720.tc720.time.sleep"


def _make_device(read_responses: list[bytes]) -> TC720:
    """
    Return a TC720 with a mock serial port pre-loaded with read() responses.
    Pads with empty bytes so read() never raises StopIteration.
    """
    tc = TC720(port="COM_TEST")
    mock_ser = MagicMock()
    mock_ser.is_open = True
    mock_ser.read.side_effect = read_responses + [b""] * 20
    tc.ser = mock_ser
    tc._connected = True
    return tc


def _make_response(temp_celsius: float) -> bytes:
    """
    Build a valid 8-byte TC720 response for a given temperature.
    Format: * D D D D S S <CR>  (asterisk + 4 hex chars + 2 checksum chars + CR)
    """
    val = int(temp_celsius * 100)
    if val < 0:
        val += 0x10000  # two's complement for negatives
    dddd = format(val, '04x')
    checksum = format(sum(ord(c) for c in dddd) & 0xFF, '02x')
    return ('*' + dddd + checksum + '\r').encode('ascii')


# ---------------------------------------------------------------------------
# calculate_checksum — TC-720 protocol checksum
# ---------------------------------------------------------------------------

class TestCalculateChecksum:

    def test_bstc_25c_produces_correct_checksum(self):
        """25°C: hex '09c4', chars ['1','c','0','9','c','4'], sum=404 → last2='94'."""
        tc = TC720(port="COM_TEST")
        bstc = ['*', '1', 'c', '0', '9', 'c', '4', 'XX', 'XX', '\r']
        result = tc.calculate_checksum(bstc)
        assert result == ['*', '1', 'c', '0', '9', 'c', '4', '9', '4', '\r']

    def test_sensor1_query_produces_correct_checksum(self):
        """Sensor1 query: cc='01', chars ['0','1','0','0','0','0'], sum=289 → last2='21'."""
        tc = TC720(port="COM_TEST")
        char_list = ['*', '0', '1', '0', '0', '0', '0', 'XX', 'XX', '\r']
        result = tc.calculate_checksum(char_list)
        assert result == ['*', '0', '1', '0', '0', '0', '0', '2', '1', '\r']

    def test_result_starts_with_asterisk(self):
        tc = TC720(port="COM_TEST")
        result = tc.calculate_checksum(['*', '0', '1', '0', '0', '0', '0', 'XX', 'XX', '\r'])
        assert result[0] == '*'

    def test_result_ends_with_carriage_return(self):
        tc = TC720(port="COM_TEST")
        result = tc.calculate_checksum(['*', '0', '1', '0', '0', '0', '0', 'XX', 'XX', '\r'])
        assert result[-1] == '\r'

    def test_result_has_ten_elements(self):
        tc = TC720(port="COM_TEST")
        result = tc.calculate_checksum(['*', '0', '1', '0', '0', '0', '0', 'XX', 'XX', '\r'])
        assert len(result) == 10


# ---------------------------------------------------------------------------
# convert_temp_to_bstc — temperature-to-command encoding
# ---------------------------------------------------------------------------

# TODO: Two test cases failed for sensor 2, need to fix code

class TestConvertTempToBstc:

    def test_25c_produces_correct_command(self):
        """25°C → 2500 hundredths → hex '09c4' → full command '*1c09c494\r'."""
        tc = TC720(port="COM_TEST")
        result = tc.convert_temp_to_bstc(25.0)
        assert ''.join(result) == '*1c09c494\r'

    def test_0c_boundary(self):
        """0°C → 0 hundredths → hex '0000' → command starts with '*1c0000'."""
        tc = TC720(port="COM_TEST")
        result = tc.convert_temp_to_bstc(0.0)
        assert ''.join(result).startswith('*1c0000')

    def test_100c_boundary(self):
        """100°C → 10000 hundredths → hex '2710' embedded in command."""
        tc = TC720(port="COM_TEST")
        result = tc.convert_temp_to_bstc(100.0)
        assert '2710' in ''.join(result)

    def test_fractional_temperature(self):
        """37.5°C → 3750 hundredths → hex '0ea6' embedded in command."""
        tc = TC720(port="COM_TEST")
        result = tc.convert_temp_to_bstc(37.5)
        assert '0ea6' in ''.join(result)

    def test_result_is_list_starting_with_asterisk(self):
        tc = TC720(port="COM_TEST")
        result = tc.convert_temp_to_bstc(25.0)
        assert isinstance(result, list)
        assert result[0] == '*'

    def test_result_ends_with_carriage_return(self):
        tc = TC720(port="COM_TEST")
        result = tc.convert_temp_to_bstc(25.0)
        assert result[-1] == '\r'


# ---------------------------------------------------------------------------
# _build_query — query command construction
# ---------------------------------------------------------------------------

class TestBuildQuery:

    def test_sensor1_query_command(self):
        """Sensor 1 → cc='01' → '*01000021\r'."""
        tc = TC720(port="COM_TEST")
        assert ''.join(tc._build_query('01')) == '*01000021\r'

    def test_sensor2_query_command(self):
        """Sensor 2 → cc='04' → '*04000024\r'."""
        tc = TC720(port="COM_TEST")
        assert ''.join(tc._build_query('04')) == '*04000024\r'

    def test_result_starts_with_asterisk(self):
        tc = TC720(port="COM_TEST")
        assert tc._build_query('01')[0] == '*'

    def test_result_ends_with_carriage_return(self):
        tc = TC720(port="COM_TEST")
        assert tc._build_query('01')[-1] == '\r'


# ---------------------------------------------------------------------------
# set_temperature — range validation and command sending
# ---------------------------------------------------------------------------

class TestSetTemperature:

    def test_below_zero_raises_value_error(self):
        tc = _make_device([])
        with pytest.raises(ValueError, match="0°C and 100°C"):
            tc.set_temperature(-0.1)

    def test_above_100_raises_value_error(self):
        tc = _make_device([])
        with pytest.raises(ValueError, match="0°C and 100°C"):
            tc.set_temperature(100.1)

    def test_boundary_0c_does_not_raise(self):
        tc = _make_device([])
        tc.set_temperature(0.0)  # must not raise

    def test_boundary_100c_does_not_raise(self):
        tc = _make_device([])
        tc.set_temperature(100.0)  # must not raise

    def test_ser_none_raises_runtime_error(self):
        tc = TC720(port="COM_TEST")
        tc.ser = None
        with pytest.raises(RuntimeError, match="not connected"):
            tc.set_temperature(25.0)

    def test_ser_not_open_raises_runtime_error(self):
        tc = TC720(port="COM_TEST")
        mock_ser = MagicMock()
        mock_ser.is_open = False
        tc.ser = mock_ser
        with pytest.raises(RuntimeError, match="not connected"):
            tc.set_temperature(25.0)

    def test_sends_ascii_encoded_bytes(self):
        tc = _make_device([])
        tc.set_temperature(25.0)
        called_bytes = tc.ser.write.call_args[0][0]
        assert isinstance(called_bytes, bytes)
        assert called_bytes.startswith(b'*')
        assert called_bytes.endswith(b'\r')

    def test_25c_sends_exact_command(self):
        """25°C must produce the exact encoded command b'*1c09c494\\r'."""
        tc = _make_device([])
        tc.set_temperature(25.0)
        tc.ser.write.assert_called_once_with(b'*1c09c494\r')

    def test_flushes_after_write(self):
        tc = _make_device([])
        tc.set_temperature(25.0)
        tc.ser.flush.assert_called_once()


# ---------------------------------------------------------------------------
# get_temperature — response parsing
# ---------------------------------------------------------------------------

class TestGetTemperature:

    def test_valid_positive_temperature(self):
        """25°C round-trip: build a valid response, parse back to 25.0."""
        tc = _make_device([_make_response(25.0)])
        with patch(_SLEEP_PATH):
            assert tc.get_temperature() == pytest.approx(25.0)

    def test_returns_float(self):
        tc = _make_device([_make_response(37.5)])
        with patch(_SLEEP_PATH):
            assert isinstance(tc.get_temperature(), float)

    def test_negative_temperature_two_complement(self):
        """-5°C is encoded as two's complement; must decode back to -5.0."""
        tc = _make_device([_make_response(-5.0)])
        with patch(_SLEEP_PATH):
            assert tc.get_temperature() == pytest.approx(-5.0)

    def test_zero_temperature(self):
        tc = _make_device([_make_response(0.0)])
        with patch(_SLEEP_PATH):
            assert tc.get_temperature() == pytest.approx(0.0)

    def test_response_too_short_raises_ioerror(self):
        tc = _make_device([b'*09c4'])  # only 5 bytes
        with patch(_SLEEP_PATH):
            with pytest.raises(IOError, match="Unexpected response"):
                tc.get_temperature()

    def test_response_not_starting_with_asterisk_raises_ioerror(self):
        tc = _make_device([b'X09c49400'])  # 8+ bytes, no leading '*'
        with patch(_SLEEP_PATH):
            with pytest.raises(IOError, match="Unexpected response"):
                tc.get_temperature()

    def test_placeholder_xxxx_raises_ioerror(self):
        """Device returning 'XXXX' (not ready) must raise IOError."""
        tc = _make_device([b'*XXXX0000'])
        with patch(_SLEEP_PATH):
            with pytest.raises(IOError, match="placeholder"):
                tc.get_temperature()

    def test_checksum_mismatch_raises_ioerror(self):
        """Corrupted checksum bytes must raise IOError."""
        valid = _make_response(25.0)
        corrupt = valid[:5] + b'ZZ' + valid[7:]  # flip checksum bytes
        tc = _make_device([corrupt])
        with patch(_SLEEP_PATH):
            with pytest.raises(IOError, match="Checksum mismatch"):
                tc.get_temperature()

    def test_non_hex_data_with_matching_checksum_raises_ioerror(self):
        """Non-hex 'ZZZZ' with its correct checksum must fail at int() parse."""
        # 'ZZZZ' checksum: sum(4 * ord('Z')) & 0xFF = (4*90) & 0xFF = 360 & 0xFF = 104 → '68'
        tc = _make_device([b'*ZZZZ68\r'])
        with patch(_SLEEP_PATH):
            with pytest.raises(IOError):
                tc.get_temperature()

    def test_sensor2_sends_sensor2_query(self):
        """sensor=2 must send the '04' query command."""
        tc = _make_device([_make_response(30.0)])
        with patch(_SLEEP_PATH):
            tc.get_temperature(sensor=2)
        assert b'04' in tc.ser.write.call_args[0][0]

    def test_sensor1_default_sends_sensor1_query(self):
        """Default sensor=1 must send the '01' query command."""
        tc = _make_device([_make_response(30.0)])
        with patch(_SLEEP_PATH):
            tc.get_temperature()
        assert b'01' in tc.ser.write.call_args[0][0]

    def test_resets_input_buffer_before_write(self):
        """reset_input_buffer() must be called to discard stale bytes."""
        tc = _make_device([_make_response(25.0)])
        with patch(_SLEEP_PATH):
            tc.get_temperature()
        tc.ser.reset_input_buffer.assert_called_once()


# ---------------------------------------------------------------------------
# status() — dict structure
# ---------------------------------------------------------------------------

class TestStatus:

    def test_disconnected_flag_returns_ok_false(self):
        tc = TC720(port="COM_TEST")
        tc._connected = False
        assert tc.status()["ok"] is False

    def test_disconnected_flag_returns_code_disconnected(self):
        tc = TC720(port="COM_TEST")
        tc._connected = False
        assert tc.status()["code"] == "disconnected"

    def test_ser_none_returns_ok_false(self):
        tc = TC720(port="COM_TEST")
        tc._connected = True
        tc.ser = None
        assert tc.status()["ok"] is False

    def test_ser_not_open_returns_ok_false(self):
        tc = TC720(port="COM_TEST")
        tc._connected = True
        mock_ser = MagicMock()
        mock_ser.is_open = False
        tc.ser = mock_ser
        assert tc.status()["ok"] is False

    def test_connected_returns_ok_true(self):
        tc = _make_device([_make_response(25.0)])
        with patch(_SLEEP_PATH):
            assert tc.status()["ok"] is True

    def test_connected_returns_code_ok(self):
        tc = _make_device([_make_response(25.0)])
        with patch(_SLEEP_PATH):
            assert tc.status()["code"] == "ok"

    def test_connected_returns_temperature_c_key(self):
        tc = _make_device([_make_response(25.0)])
        with patch(_SLEEP_PATH):
            assert "temperature_c" in tc.status()

    def test_connected_temperature_c_is_float(self):
        tc = _make_device([_make_response(25.0)])
        with patch(_SLEEP_PATH):
            assert isinstance(tc.status()["temperature_c"], float)

    def test_connected_temperature_c_correct_value(self):
        tc = _make_device([_make_response(37.5)])
        with patch(_SLEEP_PATH):
            assert tc.status()["temperature_c"] == pytest.approx(37.5)

    def test_get_temperature_error_returns_no_response_code(self):
        """If get_temperature raises, status() must return code='no_response'."""
        tc = _make_device([b'*XXXX0000'])  # placeholder → IOError in get_temperature
        with patch(_SLEEP_PATH):
            result = tc.status()
        assert result["ok"] is False
        assert result["code"] == "no_response"
