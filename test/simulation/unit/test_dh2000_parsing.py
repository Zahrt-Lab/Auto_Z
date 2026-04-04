"""
Unit tests for DH2000 light source controller — pure logic, no real serial hardware.

A MagicMock is attached directly to dh.ser so no COM port is opened.
time.sleep and _drain are patched out so tests run instantly.
Each test covers a single piece of logic in isolation.
"""

import pytest
from unittest.mock import MagicMock, patch, call

from devices.industry_components.uv_detectors.dh2000 import DH2000LightSource


# ---------------------------------------------------------------------------
# Patch targets
# ---------------------------------------------------------------------------

_SLEEP_PATH = "devices.industry_components.uv_detectors.dh2000.time.sleep"
_DRAIN_PATH = "devices.industry_components.uv_detectors.dh2000.DH2000LightSource._drain"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_device(readline_responses: list) -> DH2000LightSource:
    """
    Return a DH2000LightSource with a mock serial port pre-loaded with
    readline() responses. Pads with empty bytes so readline() never raises.
    """
    dh = DH2000LightSource(port="COM_TEST", timeout=2.0)
    mock_ser = MagicMock()
    mock_ser.in_waiting = 0
    mock_ser.readline.side_effect = [
        r if isinstance(r, bytes) else r.encode("utf-8") for r in readline_responses
    ] + [b""] * 30
    dh.ser = mock_ser
    return dh


# ---------------------------------------------------------------------------
# _readline_str — decoding and stripping
# ---------------------------------------------------------------------------


class TestReadlineStr:

    def test_returns_decoded_stripped_string(self):
        dh = _make_device([b"Shutter: OPEN\r\n"])
        with patch(_SLEEP_PATH):
            result = dh._readline_str()
        assert result == "Shutter: OPEN"

    def test_returns_empty_string_when_ser_is_none(self):
        dh = DH2000LightSource(port="COM_TEST")
        dh.ser = None
        assert dh._readline_str() == ""

    def test_returns_empty_string_on_empty_readline(self):
        dh = _make_device([b""])
        assert dh._readline_str() == ""

    def test_strips_leading_and_trailing_whitespace(self):
        dh = _make_device([b"  OK  \r\n"])
        result = dh._readline_str()
        assert result == "OK"


# ---------------------------------------------------------------------------
# dh2000_command — validation and byte sending
# ---------------------------------------------------------------------------


class TestDh2000Command:

    def test_ser_none_raises_runtime_error(self):
        dh = DH2000LightSource(port="COM_TEST")
        dh.ser = None
        with pytest.raises(RuntimeError, match="not connected"):
            dh.dh2000_command("o")

    def test_command_not_single_char_raises_value_error(self):
        dh = _make_device([b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            with pytest.raises(ValueError, match="single character"):
                dh.dh2000_command("oo")

    def test_empty_command_raises_value_error(self):
        dh = _make_device([b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            with pytest.raises(ValueError, match="single character"):
                dh.dh2000_command("")

    def test_invalid_char_raises_value_error(self):
        dh = _make_device([b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            with pytest.raises(ValueError, match="Invalid command character"):
                dh.dh2000_command("z")

    def test_valid_command_sends_encoded_bytes(self):
        dh = _make_device([b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.dh2000_command("o")
        dh.ser.write.assert_called_once_with(b"o")

    def test_flush_called_after_write(self):
        dh = _make_device([b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.dh2000_command("o")
        dh.ser.flush.assert_called_once()

    def test_write_called_before_flush(self):
        dh = _make_device([b"OK\r\n"])
        call_order = []
        dh.ser.write.side_effect = lambda _: call_order.append("write")
        dh.ser.flush.side_effect = lambda: call_order.append("flush")
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.dh2000_command("o")
        assert call_order.index("write") < call_order.index("flush")

    def test_expect_ok_false_returns_without_reading(self):
        """expect_ok=False should not read any response lines."""
        dh = _make_device([])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.dh2000_command("s", expect_ok=False)
        dh.ser.readline.assert_not_called()

    def test_expect_ok_true_reads_until_ok_found(self):
        dh = _make_device([b"Toggled.\r\n", b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.dh2000_command("h", expect_ok=True)  # must not raise
        assert dh.ser.readline.call_count >= 1

    def test_all_valid_commands_accepted(self):
        """All 6 documented commands must not raise ValueError."""
        for cmd in ("o", "c", "h", "d", "s", "x"):
            dh = _make_device([b"OK\r\n"])
            with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
                dh.dh2000_command(cmd, expect_ok=False)  # skip OK-reading for speed


# ---------------------------------------------------------------------------
# shutter_open / shutter_close — command characters
# ---------------------------------------------------------------------------


class TestShutterCommands:

    def test_shutter_open_sends_o(self):
        dh = _make_device([b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.shutter_open()
        dh.ser.write.assert_called_once_with(b"o")

    def test_shutter_close_sends_c(self):
        dh = _make_device([b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.shutter_close()
        dh.ser.write.assert_called_once_with(b"c")


# ---------------------------------------------------------------------------
# halogen_toggle / deuterium_toggle — command characters
# ---------------------------------------------------------------------------


class TestLampCommands:

    def test_halogen_toggle_sends_h(self):
        dh = _make_device([b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.halogen_toggle()
        dh.ser.write.assert_called_once_with(b"h")

    def test_deuterium_toggle_sends_d(self):
        dh = _make_device([b"OK\r\n"])
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.deuterium_toggle()
        dh.ser.write.assert_called_once_with(b"d")


# ---------------------------------------------------------------------------
# status() — response parsing
# ---------------------------------------------------------------------------


class TestStatusParsing:

    def _status_from(self, lines: list) -> dict:
        """Helper: feed status lines, return parsed dict."""
        dh = _make_device(lines)
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            return dh.status()

    def test_shutter_open_parsed_true(self):
        result = self._status_from(
            [b"Shutter: OPEN\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n"]
        )
        assert result["shutter_open"] is True

    def test_shutter_closed_parsed_false(self):
        result = self._status_from(
            [b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n"]
        )
        assert result["shutter_open"] is False

    def test_halogen_on_parsed_true(self):
        result = self._status_from(
            [b"Shutter: CLOSED\r\n", b"Halogen: ON\r\n", b"Deuterium: OFF\r\n"]
        )
        assert result["halogen_on"] is True

    def test_halogen_off_parsed_false(self):
        result = self._status_from(
            [b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n"]
        )
        assert result["halogen_on"] is False

    def test_deuterium_on_parsed_true(self):
        result = self._status_from(
            [b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: ON\r\n"]
        )
        assert result["deuterium_on"] is True

    def test_deuterium_off_parsed_false(self):
        result = self._status_from(
            [b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n"]
        )
        assert result["deuterium_on"] is False

    def test_result_contains_all_expected_keys(self):
        result = self._status_from(
            [b"Shutter: OPEN\r\n", b"Halogen: ON\r\n", b"Deuterium: ON\r\n"]
        )
        assert {
            "shutter_open",
            "halogen_on",
            "deuterium_on",
            "arduino_output",
        } <= result.keys()

    def test_arduino_output_is_list(self):
        result = self._status_from(
            [b"Shutter: OPEN\r\n", b"Halogen: ON\r\n", b"Deuterium: ON\r\n"]
        )
        assert isinstance(result["arduino_output"], list)

    def test_arduino_output_contains_raw_lines(self):
        result = self._status_from(
            [b"Shutter: OPEN\r\n", b"Halogen: ON\r\n", b"Deuterium: ON\r\n"]
        )
        assert any("Shutter" in line for line in result["arduino_output"])

    def test_all_lamps_on_shutter_open(self):
        result = self._status_from(
            [b"Shutter: OPEN\r\n", b"Halogen: ON\r\n", b"Deuterium: ON\r\n"]
        )
        assert result["shutter_open"] is True
        assert result["halogen_on"] is True
        assert result["deuterium_on"] is True

    def test_all_lamps_off_shutter_closed(self):
        result = self._status_from(
            [b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n"]
        )
        assert result["shutter_open"] is False
        assert result["halogen_on"] is False
        assert result["deuterium_on"] is False

    def test_status_sends_s_command(self):
        dh = _make_device(
            [b"Shutter: CLOSED\r\n", b"Halogen: OFF\r\n", b"Deuterium: OFF\r\n"]
        )
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.status()
        dh.ser.write.assert_called_once_with(b"s")


# ---------------------------------------------------------------------------
# safe_shutdown() — happy path: already in safe state
# ---------------------------------------------------------------------------


class TestSafeShutdownParsing:

    def test_safe_shutdown_does_not_raise_when_already_off(self):
        """If all already off + shutter closed, safe_shutdown should return without error."""
        # status() calls: 3 calls to status() (pre-check, post-lamps, verify)
        # Each status call reads 3 lines
        status_lines = [
            b"Shutter: CLOSED\r\n",
            b"Halogen: OFF\r\n",
            b"Deuterium: OFF\r\n",
        ] * 5
        dh = _make_device(status_lines)
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.safe_shutdown()  # must not raise

    def test_safe_shutdown_closes_shutter_when_open(self):
        """If shutter is open, safe_shutdown must send the 'c' (shutter_close) command.

        safe_shutdown flow:
          status1 (3 lines) → shutter_close OK (1 line) → status2 (3 lines) → status3 (3 lines)
        """
        readline_responses = [
            b"Shutter: OPEN\r\n",
            b"Halogen: OFF\r\n",
            b"Deuterium: OFF\r\n",  # status1
            b"OK\r\n",  # shutter_close
            b"Shutter: CLOSED\r\n",
            b"Halogen: OFF\r\n",
            b"Deuterium: OFF\r\n",  # status2
            b"Shutter: CLOSED\r\n",
            b"Halogen: OFF\r\n",
            b"Deuterium: OFF\r\n",  # status3 (verify)
        ]
        dh = _make_device(readline_responses)
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.safe_shutdown()
        written = [c.args[0] for c in dh.ser.write.call_args_list]
        assert b"c" in written  # shutter_close command sent

    def test_safe_shutdown_toggles_halogen_when_on(self):
        """If halogen is on, safe_shutdown must send the 'h' (halogen_toggle) command.

        safe_shutdown flow:
          status1 (3 lines) → status2 (3 lines) → halogen_toggle OK (1 line) → status3 (3 lines)
        """
        readline_responses = [
            b"Shutter: CLOSED\r\n",
            b"Halogen: ON\r\n",
            b"Deuterium: OFF\r\n",  # status1
            b"Shutter: CLOSED\r\n",
            b"Halogen: ON\r\n",
            b"Deuterium: OFF\r\n",  # status2
            b"OK\r\n",  # halogen_toggle
            b"Shutter: CLOSED\r\n",
            b"Halogen: OFF\r\n",
            b"Deuterium: OFF\r\n",  # status3 (verify)
        ]
        dh = _make_device(readline_responses)
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.safe_shutdown()
        written = [c.args[0] for c in dh.ser.write.call_args_list]
        assert b"h" in written

    def test_safe_shutdown_toggles_deuterium_when_on(self):
        """If deuterium is on, safe_shutdown must send the 'd' (deuterium_toggle) command.

        safe_shutdown flow:
          status1 (3 lines) → status2 (3 lines) → deuterium_toggle OK (1 line) → status3 (3 lines)
        """
        readline_responses = [
            b"Shutter: CLOSED\r\n",
            b"Halogen: OFF\r\n",
            b"Deuterium: ON\r\n",  # status1
            b"Shutter: CLOSED\r\n",
            b"Halogen: OFF\r\n",
            b"Deuterium: ON\r\n",  # status2
            b"OK\r\n",  # deuterium_toggle
            b"Shutter: CLOSED\r\n",
            b"Halogen: OFF\r\n",
            b"Deuterium: OFF\r\n",  # status3 (verify)
        ]
        dh = _make_device(readline_responses)
        with patch(_SLEEP_PATH), patch(_DRAIN_PATH):
            dh.safe_shutdown()
        written = [c.args[0] for c in dh.ser.write.call_args_list]
        assert b"d" in written
