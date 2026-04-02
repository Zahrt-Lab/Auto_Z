"""
Hardware tests for the VICI M6 syringe pump — require a physical pump.

Tests are skipped automatically if no VICI pump is detected (see vici_m6_device).
Flows stay at or below 250 uL/min with <= 50 uL volumes for safety.
"""

import pytest

pytestmark = [pytest.mark.hardware, pytest.mark.vici_m6]


class TestConnectHardware:

    def test_serial_is_open_after_connect(self, vici_m6_device):
        assert vici_m6_device.ser is not None
        assert vici_m6_device.ser.is_open is True

    def test_defaults_to_aspirating_direction(self, vici_m6_device):
        assert vici_m6_device.direction == "aspirating"


class TestStatusHardware:

    def test_status_returns_numeric_flow_rate(self, vici_m6_device):
        result = vici_m6_device.status()
        assert isinstance(result, (int, float))

    def test_status_reflects_updated_steps_per_ul(self, vici_m6_device):
        vici_m6_device.set_flow_rate(200.0, "dispensing")
        result = vici_m6_device.status()
        assert isinstance(result, (int, float))


class TestSetFlowRateHardware:

    def test_set_flow_rate_updates_direction(self, vici_m6_device):
        vici_m6_device.set_flow_rate(200.0, "dispensing")
        assert vici_m6_device.direction == "dispensing"

    def test_set_flow_rate_updates_internal_state(self, vici_m6_device):
        vici_m6_device.set_flow_rate(150.0, "aspirating")
        assert vici_m6_device.flow_rate_min == 150.0
        assert vici_m6_device.direction_multiplier == -1

## No need to test the aspirating, because it can contaminate the reservoir
# class TestAspirateHardware:

#     def test_aspirate_small_volume_does_not_raise(self, vici_m6_device):
#         try:
#             vici_m6_device.aspirate(flow_rate=200, volume=25)
#         finally:
#             vici_m6_device.stop()


class TestDispenseHardware:

    def test_dispense_small_volume_does_not_raise(self, vici_m6_device):
        try:
            vici_m6_device.dispense(flow_rate=200, volume=25)
        finally:
            vici_m6_device.stop()


class TestStopHardware:

    def test_stop_when_idle_does_not_raise(self, vici_m6_device):
        vici_m6_device.stop()
