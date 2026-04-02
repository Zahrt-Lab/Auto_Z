"""
Hardware tests for TC720 temperature controller — require a real device on a COM port.

These tests are auto-skipped if no TC720 is detected.
The device is detected and connected once per session via conftest.py.

Safety constraints:
  - All set_temperature calls use 25°C (safe ambient default)
  - No extreme temperatures are commanded during tests
  - Teardown in conftest.py always returns to 25°C before closing
"""

import pytest

pytestmark = [pytest.mark.hardware, pytest.mark.tc720]


# ---------------------------------------------------------------------------
# connect() — real device response
# ---------------------------------------------------------------------------

class TestConnectHardware:

    def test_connect_sets_connected_true(self, tc720_device):
        """A successfully connected device must report _connected=True."""
        assert tc720_device._connected is True

    def test_ser_is_open_after_connect(self, tc720_device):
        """The underlying serial port must be open after connect()."""
        assert tc720_device.ser is not None
        assert tc720_device.ser.is_open is True


# ---------------------------------------------------------------------------
# set_temperature() — real device acceptance
# ---------------------------------------------------------------------------

class TestSetTemperatureHardware:

    def test_set_temperature_25c_does_not_raise(self, tc720_device):
        """set_temperature(25.0) — safe ambient target — must not raise."""
        tc720_device.set_temperature(25.0)  # must not raise

    def test_set_temperature_below_range_raises_value_error(self, tc720_device):
        """Range validation must fire before any serial write (no hardware needed)."""
        with pytest.raises(ValueError, match="0°C and 100°C"):
            tc720_device.set_temperature(-1.0)

    def test_set_temperature_above_range_raises_value_error(self, tc720_device):
        with pytest.raises(ValueError, match="0°C and 100°C"):
            tc720_device.set_temperature(101.0)


# ---------------------------------------------------------------------------
# get_temperature() — real device response
# ---------------------------------------------------------------------------

class TestGetTemperatureHardware:

    def test_sensor1_returns_plausible_float(self, tc720_device):
        """Sensor 1 (INPUT1) must return a temperature in a plausible lab range."""
        result = tc720_device.get_temperature(sensor=1)
        assert isinstance(result, float), f"Expected float, got {type(result)}"
        assert -20.0 < result < 150.0, f"Temperature out of plausible range: {result}°C"

    def test_sensor2_returns_plausible_float(self, tc720_device):
        """Sensor 2 (INPUT2) must return a temperature in a plausible lab range."""
        result = tc720_device.get_temperature(sensor=2)
        assert isinstance(result, float), f"Expected float, got {type(result)}"
        assert -20.0 < result < 150.0, f"Temperature out of plausible range: {result}°C"

    def test_sensor1_and_sensor2_readings_are_close(self, tc720_device):
        """
        Both sensors read the same bath — values should be within 10°C of each other
        under normal (non-ramping) conditions.
        """
        t1 = tc720_device.get_temperature(sensor=1)
        t2 = tc720_device.get_temperature(sensor=2)
        assert abs(t1 - t2) < 10.0, (
            f"Sensor readings unexpectedly far apart: sensor1={t1}°C, sensor2={t2}°C"
        )


# ---------------------------------------------------------------------------
# status() — real device response
# ---------------------------------------------------------------------------

class TestStatusHardware:

    def test_status_returns_ok_true(self, tc720_device):
        result = tc720_device.status()
        assert result["ok"] is True, \
            f"status() returned ok=False: code={result.get('code')}, msg={result.get('msg')}"

    def test_status_contains_expected_keys(self, tc720_device):
        result = tc720_device.status()
        assert {"ok", "code", "msg", "temperature_c"} <= result.keys(), \
            f"Missing keys in status dict: {result}"

    def test_status_temperature_c_is_plausible_float(self, tc720_device):
        result = tc720_device.status()
        assert result["ok"] is True, f"Cannot check temperature: {result}"
        temp = result["temperature_c"]
        assert isinstance(temp, float), f"temperature_c should be float, got {type(temp)}"
        assert -20.0 < temp < 150.0, f"temperature_c out of plausible range: {temp}°C"

    def test_status_code_is_ok_string(self, tc720_device):
        result = tc720_device.status()
        assert result["code"] == "ok"

    def test_status_temperature_consistent_with_get_temperature(self, tc720_device):
        """status() and get_temperature() should agree within 1°C."""
        direct = tc720_device.get_temperature(sensor=1)
        via_status = tc720_device.status()["temperature_c"]
        assert abs(direct - via_status) < 1.0, (
            f"Inconsistent readings: get_temperature={direct}°C, "
            f"status temperature_c={via_status}°C"
        )
