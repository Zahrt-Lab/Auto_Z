"""
Integration tests for TC720 temperature controller — full command sequences
with mocked serial.

Unlike unit tests (which attach a MagicMock directly to tc.ser), these tests
patch serial.Serial at the module level so connect() is exercised end-to-end.
time.sleep is also patched to keep the suite fast.
"""

import pytest
from unittest.mock import MagicMock, patch, call

from temperature_controller.tc720.tc720 import TC720

# Patch targets: where serial and time are imported inside the module under test
_SERIAL_PATH = "temperature_controller.tc720.tc720.serial.Serial"
_SLEEP_PATH  = "temperature_controller.tc720.tc720.time.sleep"


def _make_response(temp_celsius: float) -> bytes:
    """Build a valid 8-byte TC720 response for a given temperature."""
    val = int(temp_celsius * 100)
    if val < 0:
        val += 0x10000
    dddd = format(val, '04x')
    checksum = format(sum(ord(c) for c in dddd) & 0xFF, '02x')
    return ('*' + dddd + checksum + '\r').encode('ascii')


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ser():
    """A pre-configured mock serial.Serial instance."""
    m = MagicMock()
    m.is_open = True
    m.read.return_value = b""
    return m


@pytest.fixture
def tc(mock_ser):
    """
    TC720 with connect() fully exercised against mock_ser.
    time.sleep is patched so no real delays occur.
    """
    with patch(_SERIAL_PATH, return_value=mock_ser), patch(_SLEEP_PATH):
        device = TC720(port="COM_TEST", baudrate=230400, timeout=1)
        device.connect()
    return device


# ---------------------------------------------------------------------------
# connect() / close() lifecycle
# ---------------------------------------------------------------------------

class TestConnectClose:

    def test_connect_opens_serial_with_correct_params(self, mock_ser):
        with patch(_SERIAL_PATH, return_value=mock_ser) as MockSerial, patch(_SLEEP_PATH):
            device = TC720(port="COM18", baudrate=230400, timeout=1)
            device.connect()
        MockSerial.assert_called_once_with(port="COM18", baudrate=230400, timeout=1)

    def test_connect_sets_ser_attribute(self, tc, mock_ser):
        assert tc.ser is mock_ser

    def test_connect_sets_connected_true(self, tc):
        assert tc._connected is True

    def test_connect_is_idempotent_when_already_open(self, mock_ser):
        """Calling connect() on an already-open port must not open a second Serial."""
        with patch(_SERIAL_PATH, return_value=mock_ser) as MockSerial, patch(_SLEEP_PATH):
            device = TC720(port="COM_TEST")
            device.connect()
            device.connect()  # second call — port already open
        MockSerial.assert_called_once()

    def test_close_sets_connected_false(self, tc):
        tc.close()
        assert tc._connected is False

    def test_close_calls_serial_close(self, tc, mock_ser):
        tc.close()
        mock_ser.close.assert_called_once()


# ---------------------------------------------------------------------------
# set_temperature() — command flow
# ---------------------------------------------------------------------------

class TestSetTemperatureFlow:

    def test_write_called_with_encoded_command(self, tc, mock_ser):
        with patch(_SLEEP_PATH):
            tc.set_temperature(25.0)
        mock_ser.write.assert_called_once_with(b'*1c09c494\r')

    def test_flush_called_after_write(self, tc, mock_ser):
        with patch(_SLEEP_PATH):
            tc.set_temperature(25.0)
        mock_ser.flush.assert_called_once()

    def test_write_called_before_flush(self, tc, mock_ser):
        """write() must precede flush()."""
        call_order = []
        mock_ser.write.side_effect  = lambda _: call_order.append("write")
        mock_ser.flush.side_effect  = lambda:   call_order.append("flush")
        with patch(_SLEEP_PATH):
            tc.set_temperature(25.0)
        assert call_order.index("write") < call_order.index("flush")

    def test_two_sequential_set_temperature_calls(self, tc, mock_ser):
        with patch(_SLEEP_PATH):
            tc.set_temperature(25.0)
            tc.set_temperature(50.0)
        # 50°C → 5000 hundredths → hex '1388'
        # chars [1:7] of bstc = ['1','c','1','3','8','8']
        # sum = 49+99+49+51+56+56 = 360, 360 & 0xFF = 104 → '68'
        # command = '*1c138868\r'
        assert mock_ser.write.call_args_list == [
            call(b'*1c09c494\r'),
            call(b'*1c138868\r'),
        ]

    def test_range_error_does_not_write_to_serial(self, tc, mock_ser):
        with pytest.raises(ValueError):
            tc.set_temperature(150.0)
        mock_ser.write.assert_not_called()


# ---------------------------------------------------------------------------
# get_temperature() — command flow and response parsing
# ---------------------------------------------------------------------------

class TestGetTemperatureFlow:

    def test_resets_input_buffer_before_query(self, tc, mock_ser):
        mock_ser.read.return_value = _make_response(25.0)
        with patch(_SLEEP_PATH):
            tc.get_temperature()
        mock_ser.reset_input_buffer.assert_called_once()

    def test_sends_sensor1_query_by_default(self, tc, mock_ser):
        mock_ser.read.return_value = _make_response(25.0)
        with patch(_SLEEP_PATH):
            tc.get_temperature()
        written = mock_ser.write.call_args[0][0]
        assert written == b'*01000021\r'

    def test_sends_sensor2_query_when_requested(self, tc, mock_ser):
        mock_ser.read.return_value = _make_response(25.0)
        with patch(_SLEEP_PATH):
            tc.get_temperature(sensor=2)
        written = mock_ser.write.call_args[0][0]
        assert written == b'*04000024\r'

    def test_parses_response_correctly(self, tc, mock_ser):
        mock_ser.read.return_value = _make_response(25.0)
        with patch(_SLEEP_PATH):
            result = tc.get_temperature()
        assert result == pytest.approx(25.0)

    def test_parses_negative_temperature(self, tc, mock_ser):
        mock_ser.read.return_value = _make_response(-5.0)
        with patch(_SLEEP_PATH):
            result = tc.get_temperature()
        assert result == pytest.approx(-5.0)

    def test_sleeps_after_write(self, tc, mock_ser):
        """A short sleep must be inserted after writing to give the device time to respond."""
        mock_ser.read.return_value = _make_response(25.0)
        with patch(_SLEEP_PATH) as mock_sleep:
            tc.get_temperature()
        mock_sleep.assert_called_once()

    def test_invalid_response_raises_ioerror(self, tc, mock_ser):
        mock_ser.read.return_value = b'garbage'
        with patch(_SLEEP_PATH):
            with pytest.raises(IOError):
                tc.get_temperature()


# ---------------------------------------------------------------------------
# status() — command flow
# ---------------------------------------------------------------------------

class TestStatusFlow:

    def test_disconnected_returns_ok_false(self, tc):
        tc._connected = False
        result = tc.status()
        assert result["ok"] is False
        assert result["code"] == "disconnected"

    def test_connected_calls_get_temperature(self, tc, mock_ser):
        mock_ser.read.return_value = _make_response(25.0)
        with patch(_SLEEP_PATH):
            tc.status()
        mock_ser.write.assert_called_once()  # query was sent

    def test_connected_returns_ok_true(self, tc, mock_ser):
        mock_ser.read.return_value = _make_response(25.0)
        with patch(_SLEEP_PATH):
            result = tc.status()
        assert result["ok"] is True

    def test_connected_returns_temperature_c(self, tc, mock_ser):
        mock_ser.read.return_value = _make_response(37.5)
        with patch(_SLEEP_PATH):
            result = tc.status()
        assert result["temperature_c"] == pytest.approx(37.5)

    def test_get_temperature_failure_returns_no_response(self, tc, mock_ser):
        """If the device returns a bad response, status() must return code='no_response'."""
        mock_ser.read.return_value = b'*XXXX0000'  # placeholder → IOError
        with patch(_SLEEP_PATH):
            result = tc.status()
        assert result["ok"] is False
        assert result["code"] == "no_response"


# ---------------------------------------------------------------------------
# stop() — safe shutdown flow
# ---------------------------------------------------------------------------

class TestStopFlow:

    def test_stop_sends_25c_set_temperature_command(self, tc, mock_ser):
        """stop() must first set temperature to the safe default of 25°C."""
        with patch(_SLEEP_PATH):
            tc.stop()
        written = [c.args[0] for c in mock_ser.write.call_args_list]
        assert b'*1c09c494\r' in written

    def test_stop_calls_serial_close(self, tc, mock_ser):
        with patch(_SLEEP_PATH):
            tc.stop()
        mock_ser.close.assert_called_once()

    def test_stop_sets_connected_false(self, tc):
        with patch(_SLEEP_PATH):
            tc.stop()
        assert tc._connected is False

    def test_stop_does_not_raise_if_set_temperature_fails(self, tc, mock_ser):
        """If set_temperature raises (e.g. mid-disconnect), stop() must still close."""
        mock_ser.is_open = False  # simulate disconnected serial mid-experiment
        with patch(_SLEEP_PATH):
            tc.stop()  # must not propagate the RuntimeError
        mock_ser.close.assert_called_once()


# ---------------------------------------------------------------------------
# Sequential workflow
# ---------------------------------------------------------------------------

class TestSequentialWorkflow:

    def test_set_temperature_then_get_temperature(self, tc, mock_ser):
        """Typical experiment step: set temperature, then read it back."""
        mock_ser.read.return_value = _make_response(25.0)
        with patch(_SLEEP_PATH):
            tc.set_temperature(25.0)
            temp = tc.get_temperature()
        assert temp == pytest.approx(25.0)
        # set_temperature write + get_temperature write = 2 total writes
        assert mock_ser.write.call_count == 2

    def test_set_temperature_then_status(self, tc, mock_ser):
        """set_temperature followed by status() reads temperature via get_temperature."""
        mock_ser.read.return_value = _make_response(50.0)
        with patch(_SLEEP_PATH):
            tc.set_temperature(50.0)
            result = tc.status()
        assert result["ok"] is True
        assert result["temperature_c"] == pytest.approx(50.0)
