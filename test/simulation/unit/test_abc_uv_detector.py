"""
Unit tests for UVDetector abstract base class.

Verifies that:
  - UVDetector cannot be instantiated directly (enforces interface)
  - Ocean_Optics_UV_vis is a concrete subclass of UVDetector
  - isinstance checks work correctly (critical for methods.py routing)
  - A user-defined subclass satisfying the full interface can be instantiated
  - A partial implementation raises TypeError on instantiation

Note: Ocean_Optics_UV_vis requires the OceanDirect SDK at init time.
      These tests use a SimUVDetector so no SDK is needed.
"""

import pytest
from abc import ABC
from unittest.mock import patch, MagicMock

from devices.industry_components.uv_detectors.uv_detector_base import UVDetector


# ---------------------------------------------------------------------------
# ABC enforcement
# ---------------------------------------------------------------------------

# Need to inspect this code
class TestUVDetectorABC:

    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            UVDetector()

    def test_is_abstract_base_class(self):
        assert issubclass(UVDetector, ABC)

    def test_abstract_methods_defined(self):
        abstract_methods = getattr(UVDetector, "__abstractmethods__", set())
        assert {"connect", "close", "status"} == abstract_methods

    def test_partial_subclass_cannot_be_instantiated(self):
        class PartialUV(UVDetector):
            def connect(self): pass
            # Missing: close, status

        with pytest.raises(TypeError):
            PartialUV()


# ---------------------------------------------------------------------------
# Ocean_Optics_UV_vis subclass check (import only, no SDK required)
# ---------------------------------------------------------------------------


class TestOceanOpticsIsSubclass:

    def test_ocean_optics_is_subclass_of_uv_detector(self):
        from devices.industry_components.uv_detectors.uv_detector import Ocean_Optics_UV_vis
        assert issubclass(Ocean_Optics_UV_vis, UVDetector)

    def test_ocean_optics_instance_is_instance_of_uv_detector(self):
        """Instantiate with a mocked OceanDirectAPI so no real SDK is needed."""
        mock_api = MagicMock()
        mock_api.return_value.find_usb_devices.return_value = 1

        with patch(
            "devices.industry_components.uv_detectors.uv_detector.OceanDirectAPI",
            mock_api,
        ):
            from devices.industry_components.uv_detectors.uv_detector import Ocean_Optics_UV_vis
            uv = Ocean_Optics_UV_vis(output_dir="/tmp")
            assert isinstance(uv, UVDetector)


# ---------------------------------------------------------------------------
# User-defined concrete subclass (simulation implementation)
# ---------------------------------------------------------------------------


class SimUVDetector(UVDetector):
    """Minimal in-memory UV detector for simulation/testing."""

    def __init__(self):
        self._connected = False
        self._model = "SimSpectrometer"

    def connect(self):
        self._connected = True

    def close(self):
        self._connected = False

    def status(self) -> dict:
        return {
            "initialized": self._connected,
            "model": self._model,
        }


class TestSimUVDetector:

    def test_can_instantiate(self):
        assert SimUVDetector() is not None

    def test_is_instance_of_abc(self):
        assert isinstance(SimUVDetector(), UVDetector)

    def test_connect_sets_initialized(self):
        sim = SimUVDetector()
        sim.connect()
        assert sim.status()["initialized"] is True

    def test_close_clears_initialized(self):
        sim = SimUVDetector()
        sim.connect()
        sim.close()
        assert sim.status()["initialized"] is False

    def test_status_returns_dict_with_required_keys(self):
        st = SimUVDetector().status()
        assert "initialized" in st

    def test_isinstance_check_for_routing(self):
        """Simulates the isinstance dispatch in methods.py."""
        assert isinstance(SimUVDetector(), UVDetector)