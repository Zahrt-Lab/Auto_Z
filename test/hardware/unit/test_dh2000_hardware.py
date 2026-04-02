"""
Hardware tests for DH2000 light source — require a real device on a COM port.

These tests are auto-skipped if no DH2000 is detected.
The device is detected and connected once per session via conftest.py.

Safety constraints:
  - safe_shutdown() is called during teardown to leave shutter closed + lamps off
  - Tests verify state rather than assuming it, to avoid wrong-direction toggles
  - No assumptions made about the initial lamp state
"""

import pytest

pytestmark = [pytest.mark.hardware, pytest.mark.dh2000]


# ---------------------------------------------------------------------------
# connect() — real device response
# ---------------------------------------------------------------------------

class TestConnectHardware:

    def test_ser_is_set_after_connect(self, dh2000_device):
        """A successfully connected device must have a non-None ser attribute."""
        assert dh2000_device.ser is not None

    def test_ser_is_open_after_connect(self, dh2000_device):
        """The underlying serial port must be open after connect()."""
        assert dh2000_device.ser.is_open is True


# ---------------------------------------------------------------------------
# shutter_open / shutter_close — real device response
# ---------------------------------------------------------------------------

class TestShutterHardware:

    def test_shutter_open_does_not_raise(self, dh2000_device):
        """shutter_open() must not raise — Arduino must respond with OK."""
        dh2000_device.shutter_open()  # must not raise

    def test_shutter_close_does_not_raise(self, dh2000_device):
        """shutter_close() must not raise — Arduino must respond with OK."""
        dh2000_device.shutter_close()  # must not raise

    def test_shutter_open_then_status_reflects_open(self, dh2000_device):
        """After shutter_open(), status() must report shutter_open=True."""
        dh2000_device.shutter_open()
        result = dh2000_device.status()
        assert result["shutter_open"] is True, \
            f"Expected shutter_open=True after shutter_open(), got: {result}"

    def test_shutter_close_then_status_reflects_closed(self, dh2000_device):
        """After shutter_close(), status() must report shutter_open=False."""
        dh2000_device.shutter_close()
        result = dh2000_device.status()
        assert result["shutter_open"] is False, \
            f"Expected shutter_open=False after shutter_close(), got: {result}"


# ---------------------------------------------------------------------------
# halogen_toggle / deuterium_toggle — real device response
# ---------------------------------------------------------------------------

class TestLampHardware:

    def test_halogen_toggle_does_not_raise(self, dh2000_device):
        """halogen_toggle() must not raise on a real device."""
        dh2000_device.halogen_toggle()  # must not raise
        dh2000_device.halogen_toggle()  # toggle back to original state

    def test_deuterium_toggle_does_not_raise(self, dh2000_device):
        """deuterium_toggle() must not raise on a real device."""
        dh2000_device.deuterium_toggle()  # must not raise
        dh2000_device.deuterium_toggle()  # toggle back to original state

    def test_halogen_toggle_changes_state(self, dh2000_device):
        """Toggling halogen must change the halogen_on state."""
        before = dh2000_device.status()["halogen_on"]
        dh2000_device.halogen_toggle()
        after = dh2000_device.status()["halogen_on"]
        assert before != after, \
            f"halogen_on should have toggled but was {before} both times"
        dh2000_device.halogen_toggle()  # restore original state

    def test_deuterium_toggle_changes_state(self, dh2000_device):
        """Toggling deuterium must change the deuterium_on state."""
        before = dh2000_device.status()["deuterium_on"]
        dh2000_device.deuterium_toggle()
        after = dh2000_device.status()["deuterium_on"]
        assert before != after, \
            f"deuterium_on should have toggled but was {before} both times"
        dh2000_device.deuterium_toggle()  # restore original state


# ---------------------------------------------------------------------------
# status() — real device response
# ---------------------------------------------------------------------------

class TestStatusHardware:

    def test_status_returns_expected_keys(self, dh2000_device):
        result = dh2000_device.status()
        assert {"shutter_open", "halogen_on", "deuterium_on", "arduino_output"} <= result.keys(), \
            f"Missing keys in status dict: {result}"

    def test_shutter_open_is_bool(self, dh2000_device):
        result = dh2000_device.status()
        assert isinstance(result["shutter_open"], bool), \
            f"shutter_open should be bool, got {type(result['shutter_open'])}"

    def test_halogen_on_is_bool(self, dh2000_device):
        result = dh2000_device.status()
        assert isinstance(result["halogen_on"], bool), \
            f"halogen_on should be bool, got {type(result['halogen_on'])}"

    def test_deuterium_on_is_bool(self, dh2000_device):
        result = dh2000_device.status()
        assert isinstance(result["deuterium_on"], bool), \
            f"deuterium_on should be bool, got {type(result['deuterium_on'])}"

    def test_arduino_output_is_non_empty_list(self, dh2000_device):
        result = dh2000_device.status()
        assert isinstance(result["arduino_output"], list), \
            f"arduino_output should be list, got {type(result['arduino_output'])}"
        assert len(result["arduino_output"]) > 0, \
            "arduino_output should not be empty"

    def test_status_consistent_across_two_calls(self, dh2000_device):
        """Two back-to-back status calls must agree (no commands in between)."""
        r1 = dh2000_device.status()
        r2 = dh2000_device.status()
        assert r1["shutter_open"] == r2["shutter_open"]
        assert r1["halogen_on"]   == r2["halogen_on"]
        assert r1["deuterium_on"] == r2["deuterium_on"]


# ---------------------------------------------------------------------------
# safe_shutdown() — real device response
# ---------------------------------------------------------------------------

class TestSafeShutdownHardware:

    def test_safe_shutdown_does_not_raise(self, dh2000_device):
        """safe_shutdown() must complete without raising."""
        dh2000_device.safe_shutdown()  # must not raise

    def test_safe_shutdown_leaves_shutter_closed(self, dh2000_device):
        """After safe_shutdown(), shutter must be closed."""
        dh2000_device.safe_shutdown()
        result = dh2000_device.status()
        assert result["shutter_open"] is False, \
            f"Shutter should be CLOSED after safe_shutdown, got: {result}"

    def test_safe_shutdown_leaves_halogen_off(self, dh2000_device):
        """After safe_shutdown(), halogen must be off."""
        dh2000_device.safe_shutdown()
        result = dh2000_device.status()
        assert result["halogen_on"] is False, \
            f"Halogen should be OFF after safe_shutdown, got: {result}"

    def test_safe_shutdown_leaves_deuterium_off(self, dh2000_device):
        """After safe_shutdown(), deuterium must be off."""
        dh2000_device.safe_shutdown()
        result = dh2000_device.status()
        assert result["deuterium_on"] is False, \
            f"Deuterium should be OFF after safe_shutdown, got: {result}"

    def test_safe_shutdown_is_idempotent(self, dh2000_device):
        """Calling safe_shutdown() twice must not raise."""
        dh2000_device.safe_shutdown()
        dh2000_device.safe_shutdown()  # already in safe state — must not raise
