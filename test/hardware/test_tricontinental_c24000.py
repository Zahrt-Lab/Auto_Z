"""
Hardware tests for Tricontinental C24000 dual-syringe pump — require a real device.

Tests are auto-skipped if no pump is detected (conftest.py scans COM17 first).
The device is connected once per session via the tricontinental_device fixture.

Safety constraints:
  - Dispense tests use small volumes (100 µL) at a moderate flow rate (500 µL/min)
  - stop() is always called after a dispense test
  - Teardown in conftest.py stops both pump heads before closing
"""

import pytest

pytestmark = [pytest.mark.hardware, pytest.mark.tricontinental]


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

class TestConnectHardware:

    def test_connect_sets_connected_true(self, tricontinental_device):
        """A successfully connected pump must report _connected=True."""
        assert tricontinental_device._connected is True

    def test_serial_is_open_after_connect(self, tricontinental_device):
        """The underlying serial port must be open after connect()."""
        assert tricontinental_device.serial is not None
        assert tricontinental_device.serial.is_open is True


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

class TestStatusHardware:

    def test_status_returns_string(self, tricontinental_device):
        """status() must return a non-empty string."""
        result = tricontinental_device.status()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_status_contains_pump_name(self, tricontinental_device):
        """status() output must include the pump's name."""
        result = tricontinental_device.status()
        assert tricontinental_device.name in result


# ---------------------------------------------------------------------------
# Stop (safe to call when idle)
# ---------------------------------------------------------------------------

class TestStopHardware:

    def test_stop_when_idle_does_not_raise(self, tricontinental_device):
        """Calling stop() on an idle pump must not raise."""
        tricontinental_device.stop()  # must not raise


# ---------------------------------------------------------------------------
# Aspirate (stub — must not raise)
# ---------------------------------------------------------------------------

class TestAspirateHardware:

    def test_aspirate_does_not_raise(self, tricontinental_device):
        """aspirate() is a stub and must not raise."""
        tricontinental_device.aspirate(500, 100)  # must not raise


# ---------------------------------------------------------------------------
# set_flow_rate
# ---------------------------------------------------------------------------

class TestSetFlowRateHardware:

    def test_set_flow_rate_stores_value(self, tricontinental_device):
        """set_flow_rate() must update the stored flow rate."""
        tricontinental_device.set_flow_rate(300.0)
        assert tricontinental_device.flow_rate_ul_min == 300.0

    def test_set_flow_rate_accepts_float(self, tricontinental_device):
        """set_flow_rate() must accept a float without raising."""
        tricontinental_device.set_flow_rate(500.0)  # must not raise


# ---------------------------------------------------------------------------
# Dispense (short, safe volume)
# ---------------------------------------------------------------------------

class TestDispenseHardware:

    def test_dispense_small_volume_does_not_raise(self, tricontinental_device):
        """Dispensing 100 µL at 500 µL/min must complete without raising."""
        try:
            tricontinental_device.dispense(flow_rate_ul_min=500, volume_ul=100)
        finally:
            tricontinental_device.stop()

    def test_dispense_invalid_flow_rate_raises(self, tricontinental_device):
        """dispense() must raise ValueError for flow_rate_ul_min <= 0."""
        with pytest.raises(ValueError):
            tricontinental_device.dispense(flow_rate_ul_min=0, volume_ul=100)

    def test_dispense_invalid_volume_raises(self, tricontinental_device):
        """dispense() must raise ValueError for volume_ul <= 0."""
        with pytest.raises(ValueError):
            tricontinental_device.dispense(flow_rate_ul_min=500, volume_ul=0)
