"""
Integration tests for DH2000 light source — full command sequences with mocked serial.

Unlike unit tests (which attach a MagicMock directly to dh.ser), these tests
patch serial.Serial at the module level so connect() is exercised end-to-end.
time.sleep and _drain are also patched to keep the suite fast.
"""

import pytest
from unittest.mock import MagicMock, patch, call

from uv_detectors.dh2000 import DH2000LightSource

# Patch targets: where serial and time are imported inside the module under test
_SERIAL_PATH = "uv_detectors.dh2000.serial.Serial"
_SLEEP_PATH  = "uv_detectors.dh2000.time.sleep"
_DRAIN_PATH  = "uv_detectors.dh2000.DH2000LightSource._drain"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_ser():
    """A pre-configured mock serial.Serial instance."""
    m = MagicMock()
    m.in_waiting = 0
    m.readline.return_value = b""
    return m


@pytest.fixture
def dh(mock_ser):
    """
    DH2000LightSource with connect() fully exercised against mock_ser.
    time.sleep and _drain are patched so no real delays or buffer loops occur.
    """
    with patch(_SERIAL_PATH, return_value=mock_ser), \
         patch(_SLEEP_PATH), \
         patch(_DRAIN_PATH):
        device = DH2000LightSource(port="COM_TEST", baudrate=9600, timeout=2.0)
        device.connect()
    return device


# ---------------------------------------------------------------------------
# connect() / close() lifecycle
# ---------------------------------------------------------------------------

class TestConnectClose:

    def test_connect_opens_serial_with_correct_params(self, mock_ser):
        with patch(_SERIAL_PATH, return_value=mock_ser) as MockSerial, \
             patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            device = DH2000LightSource(port="COM27", baudrate=9600, timeout=2.0)
            device.connect()
        MockSerial.assert_called_once_with("COM27", baudrate=9600, timeout=2.0)

    def test_connect_sets_ser_attribute(self, dh, mock_ser):
        assert dh.ser is mock_ser

    def test_close_sets_ser_to_none(self, dh):
        dh.close()
        assert dh.ser is None

    def test_close_calls_serial_close(self, dh, mock_ser):
        dh.close()
        mock_ser.close.assert_called_once()

    def test_close_is_idempotent(self, dh):
        """close() called twice must not raise."""
        dh.close()
        dh.close()  # second call — ser is already None


# ---------------------------------------------------------------------------
# _drain — buffer-clearing behaviour
# ---------------------------------------------------------------------------

class TestDrainFlow:

    def test_drain_uses_read_not_readline(self, dh):
        dh.ser.in_waiting = 5
        with patch(_SLEEP_PATH):
            dh._drain(seconds=0.0)
        dh.ser.read.assert_called()
        dh.ser.readline.assert_not_called()

    def test_drain_does_nothing_when_ser_is_none(self):
        device = DH2000LightSource(port="COM_TEST")
        device.ser = None
        device._drain(seconds=0.1)  # must not raise


# ---------------------------------------------------------------------------
# shutter_open / shutter_close — command flow
# ---------------------------------------------------------------------------

class TestShutterFlow:

    def test_shutter_open_sends_o_byte(self, dh, mock_ser):
        mock_ser.readline.return_value = b"OK\r\n"
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.shutter_open()
        mock_ser.write.assert_called_once_with(b"o")

    def test_shutter_close_sends_c_byte(self, dh, mock_ser):
        mock_ser.readline.return_value = b"OK\r\n"
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.shutter_close()
        mock_ser.write.assert_called_once_with(b"c")

    def test_shutter_open_flushes_after_write(self, dh, mock_ser):
        mock_ser.readline.return_value = b"OK\r\n"
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.shutter_open()
        mock_ser.flush.assert_called_once()

    def test_shutter_close_flushes_after_write(self, dh, mock_ser):
        mock_ser.readline.return_value = b"OK\r\n"
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.shutter_close()
        mock_ser.flush.assert_called_once()


# ---------------------------------------------------------------------------
# halogen_toggle / deuterium_toggle — command flow
# ---------------------------------------------------------------------------

class TestLampFlow:

    def test_halogen_toggle_sends_h_byte(self, dh, mock_ser):
        mock_ser.readline.return_value = b"OK\r\n"
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.halogen_toggle()
        mock_ser.write.assert_called_once_with(b"h")

    def test_deuterium_toggle_sends_d_byte(self, dh, mock_ser):
        mock_ser.readline.return_value = b"OK\r\n"
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.deuterium_toggle()
        mock_ser.write.assert_called_once_with(b"d")

    def test_halogen_toggle_flushes_after_write(self, dh, mock_ser):
        mock_ser.readline.return_value = b"OK\r\n"
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.halogen_toggle()
        mock_ser.flush.assert_called_once()

    def test_deuterium_toggle_flushes_after_write(self, dh, mock_ser):
        mock_ser.readline.return_value = b"OK\r\n"
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.deuterium_toggle()
        mock_ser.flush.assert_called_once()


# ---------------------------------------------------------------------------
# status() — command flow and response parsing
# ---------------------------------------------------------------------------

class TestStatusFlow:

    def test_status_sends_s_byte(self, dh, mock_ser):
        mock_ser.readline.side_effect = [
            b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n",
        ] + [b""] * 10
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.status()
        mock_ser.write.assert_called_once_with(b"s")

    def test_status_does_not_send_expect_ok_read(self, dh, mock_ser):
        """status uses expect_ok=False — no extra readline for OK."""
        mock_ser.readline.side_effect = [
            b"Shutter: OPEN\r\n", b"Halogen: ON\r\n", b"Deuterium: ON\r\n",
        ] + [b""] * 10
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            result = dh.status()
        # Only 1 write (the 's' command) and flush called once
        mock_ser.write.assert_called_once_with(b"s")

    def test_status_returns_parsed_dict(self, dh, mock_ser):
        mock_ser.readline.side_effect = [
            b"Shutter: OPEN\r\n", b"Halogen: ON\r\n", b"Deuterium: OFF\r\n",
        ] + [b""] * 10
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            result = dh.status()
        assert result["shutter_open"] is True
        assert result["halogen_on"] is True
        assert result["deuterium_on"] is False

    def test_status_result_contains_arduino_output(self, dh, mock_ser):
        mock_ser.readline.side_effect = [
            b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: ON\r\n",
        ] + [b""] * 10
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            result = dh.status()
        assert isinstance(result["arduino_output"], list)
        assert len(result["arduino_output"]) == 3


# ---------------------------------------------------------------------------
# safe_shutdown() — command flow (happy path: already off)
# ---------------------------------------------------------------------------

class TestSafeShutdownFlow:

    def test_safe_shutdown_does_not_raise_when_already_off(self, dh, mock_ser):
        """All off + shutter closed → safe_shutdown returns cleanly."""
        mock_ser.readline.side_effect = (
            [b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n"] * 5
            + [b""] * 10
        )
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.safe_shutdown()  # must not raise

    def test_safe_shutdown_only_sends_s_when_already_off(self, dh, mock_ser):
        """No toggle commands should be sent if state is already safe."""
        mock_ser.readline.side_effect = (
            [b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n"] * 5
            + [b""] * 10
        )
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.safe_shutdown()
        written = [c.args[0] for c in mock_ser.write.call_args_list]
        # Only 's' commands (for the 3 status() calls inside safe_shutdown)
        assert all(b == b"s" for b in written)

    def test_safe_shutdown_sends_shutter_close_when_open(self, dh, mock_ser):
        mock_ser.readline.side_effect = [
            b"Shutter: OPEN\r\n",   b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n",  # status1
            b"OK\r\n",                                                              # shutter_close
            b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n",  # status2
            b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n",  # status3 verify
        ] + [b""] * 10
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.safe_shutdown()
        written = [c.args[0] for c in mock_ser.write.call_args_list]
        assert b"c" in written

    def test_safe_shutdown_sends_halogen_toggle_when_on(self, dh, mock_ser):
        mock_ser.readline.side_effect = [
            b"Shutter: CLOSED\r\n", b"Halogen: ON\r\n",  b"Deuterium: OFF\r\n",  # status1
            b"Shutter: CLOSED\r\n", b"Halogen: ON\r\n",  b"Deuterium: OFF\r\n",  # status2
            b"OK\r\n",                                                              # halogen_toggle
            b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n",  # status3 verify
        ] + [b""] * 10
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.safe_shutdown()
        written = [c.args[0] for c in mock_ser.write.call_args_list]
        assert b"h" in written

    def test_safe_shutdown_sends_deuterium_toggle_when_on(self, dh, mock_ser):
        mock_ser.readline.side_effect = [
            b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: ON\r\n",   # status1
            b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: ON\r\n",   # status2
            b"OK\r\n",                                                              # deuterium_toggle
            b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n",  # status3 verify
        ] + [b""] * 10
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.safe_shutdown()
        written = [c.args[0] for c in mock_ser.write.call_args_list]
        assert b"d" in written


# ---------------------------------------------------------------------------
# Sequential workflow
# ---------------------------------------------------------------------------

class TestSequentialWorkflow:

    def test_shutter_open_then_status(self, dh, mock_ser):
        """Typical usage: open shutter, then query status."""
        mock_ser.readline.side_effect = [
            b"OK\r\n",                                                             # shutter_open
            b"Shutter: OPEN\r\n", b"Halogen: ON\r\n", b"Deuterium: ON\r\n",     # status
        ] + [b""] * 10
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.shutter_open()
            result = dh.status()
        assert result["shutter_open"] is True

    def test_toggle_halogen_then_deuterium(self, dh, mock_ser):
        """Toggle both lamps in sequence — each sends its own command."""
        mock_ser.readline.side_effect = [
            b"OK\r\n",  # halogen_toggle
            b"OK\r\n",  # deuterium_toggle
        ] + [b""] * 10
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.halogen_toggle()
            dh.deuterium_toggle()
        written = [c.args[0] for c in mock_ser.write.call_args_list]
        assert written == [b"h", b"d"]
