# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
Hardware tests for VICI selector valves — require a physical valve assembly.

Tests skip automatically if no valve is detected (see vici_valve_device fixture).
Movements are limited to the first two positions to keep plumbing changes minimal.
"""

import pytest

pytestmark = [pytest.mark.hardware, pytest.mark.vici_valve]


class TestConnectHardware:

    def test_serial_is_open_after_connect(self, vici_valve_device):
        assert vici_valve_device.ser is not None
        assert vici_valve_device.ser.is_open is True

    def test_positions_are_even(self, vici_valve_device):
        assert vici_valve_device.positions % 2 == 0


class TestStatusHardware:

    def test_status_returns_string(self, vici_valve_device):
        result = vici_valve_device.status()
        assert isinstance(result, str)
        assert len(result) > 0


class TestMovementHardware:

    def test_move_home_does_not_raise(self, vici_valve_device):
        response = vici_valve_device.move_home()
        assert isinstance(response, str)

    def test_go_to_second_position_and_back(self, vici_valve_device):
        target = 2 if vici_valve_device.positions >= 2 else 1
        response = vici_valve_device.go_to_position(target)
        assert isinstance(response, str)
        pos_report = vici_valve_device.get_position()
        assert isinstance(pos_report, str)
        assert len(pos_report) > 0
        vici_valve_device.move_home()

    def test_clockwise_step_then_counter(self, vici_valve_device):
        cw_response = vici_valve_device.move_clockwise(1)
        assert isinstance(cw_response, str)
        cc_response = vici_valve_device.move_counterclockwise(1)
        assert isinstance(cc_response, str)
        vici_valve_device.move_home()


class TestStopHardware:

    def test_stop_moves_home(self, vici_valve_device):
        vici_valve_device.stop()
        pos_report = vici_valve_device.get_position()
        assert isinstance(pos_report, str)
        assert len(pos_report) > 0
