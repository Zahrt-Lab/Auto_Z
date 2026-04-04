"""
Unit tests for DH2000Controller abstract base class.

Verifies that:
  - DH2000Controller cannot be instantiated directly (enforces interface)
  - DH2000LightSource is a concrete subclass of DH2000Controller
  - isinstance checks work correctly (critical for methods.py routing)
  - A user-defined subclass satisfying the full interface can be instantiated
  - A partial implementation raises TypeError on instantiation
"""

import pytest
from abc import ABC

from devices.industry_components.uv_detectors.dh2000_base import DH2000Controller
from devices.industry_components.uv_detectors.dh2000 import DH2000LightSource


# ---------------------------------------------------------------------------
# ABC enforcement
# ---------------------------------------------------------------------------


class TestDH2000ControllerABC:

    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            DH2000Controller()

    def test_is_abstract_base_class(self):
        assert issubclass(DH2000Controller, ABC)

    def test_abstract_methods_defined(self):
        abstract_methods = getattr(DH2000Controller, "__abstractmethods__", set())
        expected = {"connect", "close", "shutter_open", "shutter_close",
                    "halogen_toggle", "deuterium_toggle", "status", "safe_shutdown"}
        assert expected == abstract_methods

    def test_partial_subclass_cannot_be_instantiated(self):
        """A subclass that only implements some abstract methods raises TypeError."""
        class PartialDH2000(DH2000Controller):
            def connect(self): pass
            def close(self): pass
            # Missing: shutter_open, shutter_close, halogen_toggle,
            #          deuterium_toggle, status, safe_shutdown

        with pytest.raises(TypeError):
            PartialDH2000()


# ---------------------------------------------------------------------------
# Concrete subclass — DH2000LightSource
# ---------------------------------------------------------------------------


class TestDH2000LightSourceIsSubclass:

    def test_dh2000_light_source_is_subclass_of_controller(self):
        assert issubclass(DH2000LightSource, DH2000Controller)

    def test_instance_is_instance_of_controller(self):
        dh = DH2000LightSource(port="COM_TEST")
        assert isinstance(dh, DH2000Controller)

    def test_instance_is_instance_of_concrete_class(self):
        dh = DH2000LightSource(port="COM_TEST")
        assert isinstance(dh, DH2000LightSource)


# ---------------------------------------------------------------------------
# User-defined concrete subclass (minimal simulation implementation)
# ---------------------------------------------------------------------------


class SimDH2000(DH2000Controller):
    """Minimal in-memory DH2000 implementation for simulation/testing."""

    def __init__(self):
        self._shutter_open = False
        self._halogen_on = False
        self._deuterium_on = False

    def connect(self): pass
    def close(self): pass
    def shutter_open(self): self._shutter_open = True
    def shutter_close(self): self._shutter_open = False
    def halogen_toggle(self): self._halogen_on = not self._halogen_on
    def deuterium_toggle(self): self._deuterium_on = not self._deuterium_on

    def status(self) -> dict:
        return {
            "shutter_open": self._shutter_open,
            "halogen_on": self._halogen_on,
            "deuterium_on": self._deuterium_on,
            "arduino_output": [],
        }

    def safe_shutdown(self):
        self._shutter_open = False
        self._halogen_on = False
        self._deuterium_on = False


class TestSimDH2000:

    def test_can_instantiate(self):
        sim = SimDH2000()
        assert sim is not None

    def test_is_instance_of_abc(self):
        assert isinstance(SimDH2000(), DH2000Controller)

    def test_shutter_open_sets_state(self):
        sim = SimDH2000()
        sim.shutter_open()
        assert sim.status()["shutter_open"] is True

    def test_shutter_close_sets_state(self):
        sim = SimDH2000()
        sim.shutter_open()
        sim.shutter_close()
        assert sim.status()["shutter_open"] is False

    def test_halogen_toggle_flips_state(self):
        sim = SimDH2000()
        sim.halogen_toggle()
        assert sim.status()["halogen_on"] is True
        sim.halogen_toggle()
        assert sim.status()["halogen_on"] is False

    def test_deuterium_toggle_flips_state(self):
        sim = SimDH2000()
        sim.deuterium_toggle()
        assert sim.status()["deuterium_on"] is True

    def test_safe_shutdown_clears_all_state(self):
        sim = SimDH2000()
        sim.shutter_open()
        sim.halogen_toggle()
        sim.deuterium_toggle()
        sim.safe_shutdown()
        st = sim.status()
        assert st["shutter_open"] is False
        assert st["halogen_on"] is False
        assert st["deuterium_on"] is False

    def test_status_returns_dict_with_required_keys(self):
        st = SimDH2000().status()
        assert {"shutter_open", "halogen_on", "deuterium_on", "arduino_output"} <= st.keys()

    def test_isinstance_check_for_routing(self):
        """Simulates the isinstance dispatch in methods.py."""
        devices = [SimDH2000(), DH2000LightSource(port="COM_TEST")]
        for device in devices:
            assert isinstance(device, DH2000Controller)