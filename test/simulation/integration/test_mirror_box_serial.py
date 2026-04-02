"""
Integration tests for MirrorBox365nm — full command sequences with mocked serial.

Unlike unit tests (which attach a MagicMock directly to mb.ser), these tests
patch serial.Serial at the module level so connect() is exercised end-to-end.
time.sleep is also patched to keep the suite fast.
"""

import pytest
from unittest.mock import MagicMock, patch, call

from custom_components.light_source.mirror_box_365nm.mirror_box_365nm import MirrorBox365nm

# Patch target: where serial is imported inside the module under test
_SERIAL_PATH = "custom_components.light_source.mirror_box_365nm.mirror_box_365nm.serial.Serial"
_SLEEP_PATH  = "custom_components.light_source.mirror_box_365nm.mirror_box_365nm.time.sleep"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ser():
    """A pre-configured mock serial.Serial instance."""
    m = MagicMock()
    m.timeout = 2.0
    m.in_waiting = 0
    m.readline.return_value = b""
    return m


@pytest.fixture
def mb(mock_ser):
    """
    MirrorBox365nm with connect() fully exercised against mock_ser.
    time.sleep is patched so no real delays occur.
    """
    with patch(_SERIAL_PATH, return_value=mock_ser), patch(_SLEEP_PATH):
        device = MirrorBox365nm(port="COM_TEST")
        device.connect()
    return device


# ---------------------------------------------------------------------------
# connect() / close() lifecycle
# ---------------------------------------------------------------------------

class TestConnectClose:

    def test_connect_opens_serial_with_correct_params(self, mock_ser):
        with patch(_SERIAL_PATH, return_value=mock_ser) as MockSerial, patch(_SLEEP_PATH):
            mb = MirrorBox365nm(port="COM18")
            mb.connect()
        MockSerial.assert_called_once_with("COM18", baudrate=9600, timeout=2.0)

    def test_connect_sets_ser_attribute(self, mb, mock_ser):
        assert mb.ser is mock_ser

    def test_close_sets_ser_to_none(self, mb):
        mb.close()
        assert mb.ser is None

    def test_close_is_idempotent(self, mb):
        """Calling close() twice must not raise."""
        mb.close()
        mb.close()   # second call should be safe
        assert mb.ser is None

    def test_close_calls_serial_close(self, mb, mock_ser):
        mb.close()
        mock_ser.close.assert_called_once()


# ---------------------------------------------------------------------------
# drain() — must use read(), not readline()
# ---------------------------------------------------------------------------

class TestDrain:

    def test_drain_uses_read_not_readline(self, mb, mock_ser):
        """drain() should consume bytes with read(in_waiting), never readline()."""
        mock_ser.in_waiting = 10
        mock_ser.readline.reset_mock()

        with patch(_SLEEP_PATH):
            mb.drain(0.1)

        mock_ser.read.assert_called()
        mock_ser.readline.assert_not_called()

    def test_drain_does_nothing_when_buffer_empty(self, mb, mock_ser):
        """When in_waiting == 0 throughout, read() should not be called."""
        mock_ser.in_waiting = 0
        mock_ser.read.reset_mock()

        with patch(_SLEEP_PATH):
            mb.drain(0.1)

        mock_ser.read.assert_not_called()


# ---------------------------------------------------------------------------
# set_dimmer() — command flow
# ---------------------------------------------------------------------------

class TestSetDimmerFlow:

    def test_write_called_before_readline(self, mb, mock_ser):
        """write() must happen before readline() reads the response."""
        call_order = []
        mock_ser.write.side_effect = lambda _: call_order.append("write")
        mock_ser.readline.side_effect = [b"OK (dimmer set)\r\n"] + [b""] * 10
        mock_ser.readline.side_effect = (
            lambda: call_order.append("read") or b"OK (dimmer set)\r\n"
        )

        mb.set_dimmer(128)

        assert call_order[0] == "write", "write() must be called before readline()"

    def test_two_sequential_dimmer_calls_write_correct_commands(self, mb, mock_ser):
        mock_ser.readline.side_effect = [
            b"OK (dimmer set)\r\n",
            b"OK (dimmer set)\r\n",
        ] + [b""] * 10
        mb.set_dimmer(0)
        mb.set_dimmer(255)
        assert mock_ser.write.call_args_list == [
            call(b"dim 0\n"),
            call(b"dim 255\n"),
        ]

    def test_set_dimmer_returns_ok(self, mb, mock_ser):
        mock_ser.readline.side_effect = [b"OK (dimmer set)\r\n"] + [b""] * 10
        result = mb.set_dimmer(128)
        assert "OK" in result


# ---------------------------------------------------------------------------
# status() — command flow
# ---------------------------------------------------------------------------

class TestStatusFlow:

    def _load_status_responses(self, mock_ser):
        mock_ser.readline.side_effect = [
            b"Light1: ON | Light2: ON | DimmerPWM: 255\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ] + [b""] * 10

    def test_writes_s_command(self, mb, mock_ser):
        self._load_status_responses(mock_ser)
        with patch(_SLEEP_PATH), patch.object(mb, "drain"):
            mb.status()
        mb.ser.write.assert_called_with(b"s\n")

    def test_drain_called_before_write(self, mb, mock_ser):
        """drain() must be invoked before the 's' command is written."""
        self._load_status_responses(mock_ser)
        call_order = []
        with patch.object(mb, "drain", side_effect=lambda *a: call_order.append("drain")), \
             patch(_SLEEP_PATH):
            original_write = mb.ser.write
            mb.ser.write = lambda b: call_order.append("write") or original_write(b)
            mb.status()
        assert call_order.index("drain") < call_order.index("write")

    def test_status_returns_fully_parsed_dict(self, mb, mock_ser):
        self._load_status_responses(mock_ser)
        with patch.object(mb, "drain"), patch(_SLEEP_PATH):
            result = mb.status()
        assert result["light1_on"] is True
        assert result["light2_on"] is True
        assert result["dimmer_pwm"] == 255
        assert result["temp_light1_c"] == pytest.approx(45.30)
        assert result["temp_light2_c"] == pytest.approx(44.80)

    def test_status_skips_stream_line_in_buffer(self, mb, mock_ser):
        """A CSV stream line arriving before the status response must be skipped."""
        mock_ser.readline.side_effect = [
            b"26.41,26.41\r\n",                               # stream — skip
            b"Light1: ON | Light2: ON | DimmerPWM: 200\r\n",
            b"Temps(C): 45.30\t44.80\r\n",
        ] + [b""] * 10
        with patch.object(mb, "drain"), patch(_SLEEP_PATH):
            result = mb.status()
        assert result["light1_on"] is True
        assert result["dimmer_pwm"] == 200


# ---------------------------------------------------------------------------
# Sequential workflow — set_dimmer then status
# ---------------------------------------------------------------------------

class TestSequentialWorkflow:

    def test_set_dimmer_then_status(self, mb, mock_ser):
        """Verify a typical experiment step: dim → check status."""
        mock_ser.readline.side_effect = [
            b"OK (dimmer set)\r\n",                           # response for set_dimmer
            b"Light1: ON | Light2: ON | DimmerPWM: 200\r\n", # response for status line1
            b"Temps(C): 45.30\t44.80\r\n",                   # response for status line2
        ] + [b""] * 10

        dim_result = mb.set_dimmer(200)
        with patch.object(mb, "drain"):
            status_result = mb.status()

        assert "OK" in dim_result
        assert status_result["dimmer_pwm"] == 200
        assert status_result["temp_light1_c"] == pytest.approx(45.30)
