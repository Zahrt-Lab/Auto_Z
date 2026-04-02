"""
Hardware tests for MirrorBox365nm — require a real Arduino on a COM port.

These tests are auto-skipped if no MirrorBox365nm is detected.
The device is detected and connected once per session via conftest.py.

Safety constraints:
  - Maximum dimmer value used in tests: 200  (never 0 = full brightness)
  - 255 is used as the "off" / safe state
"""

import pytest

pytestmark = [pytest.mark.hardware, pytest.mark.mirror_box]


# ---------------------------------------------------------------------------
# set_dimmer — real Arduino response
# ---------------------------------------------------------------------------

class TestSetDimmerHardware:

    def test_set_dimmer_200_returns_ok(self, mirror_box_device):
        """set_dimmer(200) should return an OK response from the Arduino."""
        result = mirror_box_device.set_dimmer(200)
        assert result is not None
        assert "OK" in result

    def test_set_dimmer_255_returns_ok(self, mirror_box_device):
        """set_dimmer(255) (off/safe state) should return an OK response."""
        result = mirror_box_device.set_dimmer(255)
        assert result is not None
        assert "OK" in result


# ---------------------------------------------------------------------------
# status() — real Arduino response
# ---------------------------------------------------------------------------

class TestStatusHardware:

    def test_returns_all_expected_keys(self, mirror_box_device):
        result = mirror_box_device.status()
        expected = {
            "light1_on", "light2_on", "dimmer_pwm",
            "temp_light1_c", "temp_light2_c",
            "raw_line1", "raw_line2",
        }
        assert set(result.keys()) == expected

    def test_light_states_are_bool(self, mirror_box_device):
        result = mirror_box_device.status()
        assert isinstance(result["light1_on"], bool), \
            f"light1_on should be bool, got {type(result['light1_on'])}: {result['raw_line1']}"
        assert isinstance(result["light2_on"], bool), \
            f"light2_on should be bool, got {type(result['light2_on'])}: {result['raw_line1']}"

    def test_dimmer_pwm_is_int_in_valid_range(self, mirror_box_device):
        result = mirror_box_device.status()
        assert isinstance(result["dimmer_pwm"], int), \
            f"dimmer_pwm should be int, got {type(result['dimmer_pwm'])}: {result['raw_line1']}"
        assert 0 <= result["dimmer_pwm"] <= 255

    def test_temperatures_are_plausible_floats(self, mirror_box_device):
        result = mirror_box_device.status()
        assert result["temp_light1_c"] is not None, \
            f"temp_light1_c is None — raw line: {result['raw_line2']}"
        assert result["temp_light2_c"] is not None, \
            f"temp_light2_c is None — raw line: {result['raw_line2']}"
        assert -50.0 < result["temp_light1_c"] < 200.0, \
            f"temp_light1_c out of plausible range: {result['temp_light1_c']}"
        assert -50.0 < result["temp_light2_c"] < 200.0, \
            f"temp_light2_c out of plausible range: {result['temp_light2_c']}"

    def test_dimmer_pwm_reflects_set_dimmer(self, mirror_box_device):
        """Full round-trip: set dimmer to 200, read back status, confirm dimmer_pwm == 200."""
        mirror_box_device.set_dimmer(200)
        result = mirror_box_device.status()
        assert result["dimmer_pwm"] == 200, \
            f"Expected dimmer_pwm=200 after set_dimmer(200), got {result['dimmer_pwm']}"
        # Return to safe state
        mirror_box_device.set_dimmer(255)


# ---------------------------------------------------------------------------
# read_temperature_stream() — real Arduino stream
# ---------------------------------------------------------------------------

class TestReadTemperatureStreamHardware:

    def test_returns_temp_light1_and_light2_keys(self, mirror_box_device):
        result = mirror_box_device.read_temperature_stream()
        assert "error" not in result, f"read_temperature_stream returned error: {result}"
        assert "temp_light1_c" in result
        assert "temp_light2_c" in result

    def test_temperatures_are_plausible_floats(self, mirror_box_device):
        result = mirror_box_device.read_temperature_stream()
        assert "error" not in result, f"read_temperature_stream returned error: {result}"
        assert -50.0 < result["temp_light1_c"] < 200.0, \
            f"temp_light1_c out of range: {result['temp_light1_c']}"
        assert -50.0 < result["temp_light2_c"] < 200.0, \
            f"temp_light2_c out of range: {result['temp_light2_c']}"

    def test_no_legacy_tc1_tc2_keys(self, mirror_box_device):
        """TC1/TC2 keys (temp_cold, temp_hot) must not appear in stream output."""
        result = mirror_box_device.read_temperature_stream()
        assert "temp_cold" not in result
        assert "temp_hot" not in result
