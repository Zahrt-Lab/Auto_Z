# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Central coordinator that delegates CSV method actions to per-device sub-executors.

Sub-executor locations (each sits next to its abstract base class):
  LiquidHandlerExecutor  — devices/industry_components/liquid_handlers/
  PumpExecutor           — devices/industry_components/pumps/
  ValveExecutor          — devices/industry_components/valves/
  TemperatureExecutor    — devices/industry_components/temperature_controller/
  UvDetectorLightSourceExecutor — devices/industry_components/uv_detectors/
  UvDetectorExecutor            — devices/industry_components/uv_detectors/
  PhotoReactorExecutor   — devices/custom_components/light_source/
"""

from devices.industry_components.liquid_handlers.liquid_handler_executor import LiquidHandlerExecutor
from devices.industry_components.liquid_handlers.bed_layout import BedLayout
from devices.industry_components.pumps.pump_executor import PumpExecutor
from devices.industry_components.valves.valve_executor import ValveExecutor
from devices.industry_components.temperature_controller.temperature_executor import TemperatureExecutor
from devices.industry_components.uv_detectors.uv_detector_light_source_executor import UvDetectorLightSourceExecutor
from devices.industry_components.uv_detectors.uv_detector_executor import UvDetectorExecutor
from devices.custom_components.photo_reactor.photo_reactor_executor import PhotoReactorExecutor

# Abstract base classes (kept here so methods.py can isinstance-check against them)
from devices.industry_components.liquid_handlers.liquid_handlers import LiquidHandler
from devices.industry_components.pumps.pumps import Pump
from devices.industry_components.valves.valves import Valves
from devices.industry_components.temperature_controller.temperature_controller import TemperatureController
from devices.industry_components.syringe_pumps.syringe_pumps import SyringePump
from devices.industry_components.uv_detectors.uv_detector_light_source_base import uv_detector_light_source_base
from devices.industry_components.uv_detectors.uv_detector_base import UVDetector
from devices.custom_components.photo_reactor.photo_reactor_base import PhotoReactor


class DeviceExecutor:
    """Thin coordinator — instantiates sub-executors and delegates all execute_* calls."""

    def __init__(self, bed_layouts, log_callback, start_time, continue_flag_getter):
        """
        Args:
            bed_layouts: Shared dict of {bed_number: BedLayout}.
            log_callback: Function to log an action row (component, action, params, output).
            start_time: Experiment start time (datetime) — reserved for future sub-executor use.
            continue_flag_getter: Callable returning bool — passed to TemperatureExecutor.
        """
        self._bed_layouts = bed_layouts
        self._log_callback = log_callback
        self._liquid_handler = LiquidHandlerExecutor(bed_layouts, log_callback)
        self._pump = PumpExecutor(log_callback)
        self._valve = ValveExecutor(log_callback)
        self._temperature = TemperatureExecutor(log_callback, continue_flag_getter)
        self._uv_detector_light_source = UvDetectorLightSourceExecutor(log_callback)
        self._uv_detector = UvDetectorExecutor(log_callback)
        self._photo_reactor = PhotoReactorExecutor(log_callback)

    # ------------------------------------------------------------------
    # Public delegation methods (interface unchanged for methods.py)
    # ------------------------------------------------------------------

    def execute_liquid_handler(self, action, params, component, liquid_handler: LiquidHandler):
        self._liquid_handler.execute(action, params, component, liquid_handler)

    def execute_pump(self, action, params, component, pump: Pump):
        self._pump.execute(action, params, component, pump)

    def stop_all_pumps(self):
        self._pump.stop_all_pumps()

    def wait_for_pumps(self):
        self._pump.wait_for_pumps()

    def execute_valve(self, action, params, component, valve: Valves):
        self._valve.execute(action, params, component, valve)

    def execute_temperature(self, action, params, component, temp_control: TemperatureController):
        self._temperature.execute(action, params, component, temp_control)

    def execute_uv_detector_light_source(self, action, params, component, dh: uv_detector_light_source_base):
        self._uv_detector_light_source.execute(action, params, component, dh)

    def execute_uv_detector(self, action, params, component, uv: UVDetector):
        self._uv_detector.execute(action, params, component, uv)

    def execute_mirror_box(self, action, params, component, mirror_box: PhotoReactor):
        self._photo_reactor.execute(action, params, component, mirror_box)

    def set_bedlayout(self, bed, rack_layout):
        """Set the layout for a specific bed with the given rack_layout."""
        bed_layout = BedLayout(bed_number=bed, rack_layout=rack_layout)
        self._bed_layouts[bed] = bed_layout
        self._log_callback("SetBedLayout", f"Bed {bed} layout set with rack_layout {rack_layout}", "", "OK")
