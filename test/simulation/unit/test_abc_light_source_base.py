"""
Unit tests for LightSourceBase abstract base class.

Verifies that:
  - LightSourceBase cannot be instantiated directly (enforces interface)
  - MirrorBox365nm is a concrete subclass of LightSourceBase
  - isinstance checks work correctly (critical for methods.py routing)
  - A user-defined subclass satisfying the full interface can be instantiated
  - A partial implementation raises TypeError on instantiation
"""

import pytest
from abc import ABC

from devices.custom_components.light_source.light_source_base import LightSourceBase
from devices.custom_components.light_source.mirror_box_365nm.mirror_box_365nm import MirrorBox365nm


# ---------------------------------------------------------------------------
# ABC enforcement
# ---------------------------------------------------------------------------


class TestLightSourceBaseABC:

    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            LightSourceBase()

    def test_is_abstract_base_class(self):
        assert issubclass(LightSourceBase, ABC)

    def test_abstract_methods_defined(self):
        abstract_methods = getattr(LightSourceBase, "__abstractmethods__", set())
        expected = {"connect", "close", "set_dimmer", "status", "read_temperature_stream"}
        assert expected == abstract_methods

    def test_partial_subclass_cannot_be_instantiated(self):
        class PartialLight(LightSourceBase):
            def connect(self): pass
            def close(self): pass
            # Missing: set_dimmer, status, read_temperature_stream

        with pytest.raises(TypeError):
            PartialLight()


# ---------------------------------------------------------------------------
# Concrete subclass — MirrorBox365nm
# ---------------------------------------------------------------------------


class TestMirrorBox365nmIsSubclass:

    def test_mirror_box_is_subclass_of_light_source_base(self):
        assert issubclass(MirrorBox365nm, LightSourceBase)

    def test_instance_is_instance_of_light_source_base(self):
        mb = MirrorBox365nm(port="COM_TEST")
        assert isinstance(mb, LightSourceBase)

    def test_instance_is_instance_of_concrete_class(self):
        mb = MirrorBox365nm(port="COM_TEST")
        assert isinstance(mb, MirrorBox365nm)


# ---------------------------------------------------------------------------
# User-defined concrete subclass (simulation implementation)
# ---------------------------------------------------------------------------


class SimLightSource(LightSourceBase):
    """Minimal in-memory light source for simulation/testing."""

    def __init__(self):
        self._dimmer = 255  # off by default
        self._connected = False
        self._temp = {"temp_light1_c": 25.0, "temp_light2_c": 25.0}

    def connect(self):
        self._connected = True

    def close(self):
        self._connected = False

    def set_dimmer(self, value: int) -> None:
        self._dimmer = max(0, min(255, value))

    def status(self) -> dict:
        return {
            "light1_on": self._dimmer < 255,
            "light2_on": self._dimmer < 255,
            "dimmer_pwm": self._dimmer,
            "temp_light1_c": self._temp["temp_light1_c"],
            "temp_light2_c": self._temp["temp_light2_c"],
        }

    def read_temperature_stream(self) -> dict:
        return self._temp.copy()


class TestSimLightSource:

    def test_can_instantiate(self):
        assert SimLightSource() is not None

    def test_is_instance_of_abc(self):
        assert isinstance(SimLightSource(), LightSourceBase)

    def test_connect_sets_connected(self):
        sim = SimLightSource()
        sim.connect()
        assert sim._connected is True

    def test_close_clears_connected(self):
        sim = SimLightSource()
        sim.connect()
        sim.close()
        assert sim._connected is False

    def test_set_dimmer_stores_value(self):
        sim = SimLightSource()
        sim.set_dimmer(128)
        assert sim._dimmer == 128

    def test_set_dimmer_clamps_to_zero(self):
        sim = SimLightSource()
        sim.set_dimmer(-10)
        assert sim._dimmer == 0

    def test_set_dimmer_clamps_to_255(self):
        sim = SimLightSource()
        sim.set_dimmer(300)
        assert sim._dimmer == 255

    def test_status_returns_dict_with_required_keys(self):
        st = SimLightSource().status()
        assert {"light1_on", "light2_on", "dimmer_pwm"} <= st.keys()

    def test_status_light_off_when_dimmer_at_255(self):
        sim = SimLightSource()
        sim.set_dimmer(255)
        assert sim.status()["light1_on"] is False

    def test_status_light_on_when_dimmer_below_255(self):
        sim = SimLightSource()
        sim.set_dimmer(0)
        assert sim.status()["light1_on"] is True

    def test_read_temperature_stream_returns_dict(self):
        result = SimLightSource().read_temperature_stream()
        assert "temp_light1_c" in result
        assert "temp_light2_c" in result

    def test_isinstance_check_for_routing(self):
        """Simulates the isinstance dispatch in methods.py."""
        devices = [SimLightSource(), MirrorBox365nm(port="COM_TEST")]
        for device in devices:
            assert isinstance(device, LightSourceBase)