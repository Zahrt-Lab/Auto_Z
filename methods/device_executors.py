# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

from __future__ import annotations

from datetime import datetime
from typing import Callable

"""
Central Device Executor that assigns actions to the appropriate device's sub-executor
"""

LogCallback = Callable[[str, str, str, str, str], None]

# Abstract base classes for each instrument type
from devices.industry_components.liquid_handlers.liquid_handlers import LiquidHandler
from devices.industry_components.pumps.pumps import Pump
from devices.industry_components.valves.valves import Valves
from devices.industry_components.temperature_controller.temperature_controller import TemperatureController
from devices.industry_components.syringe_pumps.syringe_pumps import SyringePump
from devices.industry_components.uv_detectors.uv_detector_light_source_base import uv_detector_light_source_base
from devices.industry_components.uv_detectors.uv_detector_base import UVDetector
from devices.custom_components.photo_reactor.photo_reactor_base import PhotoReactor

# Sub-executors for each instrument type
from devices.industry_components.liquid_handlers.liquid_handler_executor import LiquidHandlerExecutor
from devices.industry_components.liquid_handlers.bed_layout import BedLayout
from devices.industry_components.pumps.pump_executor import PumpExecutor
from devices.industry_components.valves.valve_executor import ValveExecutor
from devices.industry_components.temperature_controller.temperature_executor import TemperatureExecutor
from devices.industry_components.uv_detectors.uv_detector_light_source_executor import UvDetectorLightSourceExecutor
from devices.industry_components.uv_detectors.uv_detector_executor import UvDetectorExecutor
from devices.custom_components.photo_reactor.photo_reactor_executor import PhotoReactorExecutor

class DeviceExecutor:
    """Central Device Executor: instantiates sub-executors and delegates all execute_* calls."""

    def __init__(
        self,
        bed_layouts: dict[int, BedLayout],
        log_callback: LogCallback,
        start_time: datetime,
        continue_flag_getter: Callable[[], bool],
    ) -> None:
        """
        Parameters:
            bed_layouts: Dictionary of {bed_number: BedLayout}.
            log_callback: Function to log an experiment action row (component, action, params, output).
            start_time: Experiment start time (datetime), used for future sub-executor use.
            continue_flag_getter: Callable returning bool, passed to the TemperatureExecutor.
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

    def execute_liquid_handler(self, action: str, params: str, component: str, liquid_handler: LiquidHandler) -> None:
        """Assigns a liquid handler action to the LiquidHandlerExecutor."""
        self._liquid_handler.execute(action, params, component, liquid_handler)

    def execute_pump(self, action: str, params: str, component: str, pump: Pump) -> None:
        """Assigns a pump action to the PumpExecutor."""
        self._pump.execute(action, params, component, pump)

    def stop_all_pumps(self) -> None:
        """Stop all pumps immediately."""
        self._pump.stop_all_pumps()

    def wait_for_pumps(self) -> None:
        self._pump.wait_for_pumps()

    def execute_valve(self, action: str, params: str, component: str, valve: Valves) -> None:
        """Assigns a valve action to the ValveExecutor."""
        self._valve.execute(action, params, component, valve)

    def execute_temperature(self, action: str, params: str, component: str, temp_control: TemperatureController) -> None:
        """Assigns a temperature control action to the TemperatureExecutor."""
        self._temperature.execute(action, params, component, temp_control)

    def execute_uv_detector_light_source(self, action: str, params: str, component: str, dh: uv_detector_light_source_base) -> None:
        """Assigns a DH2000 light source action to the UvDetectorLightSourceExecutor."""
        self._uv_detector_light_source.execute(action, params, component, dh)

    def execute_uv_detector(self, action: str, params: str, component: str, uv: UVDetector) -> None:
        """Assigns a UV detector action to the UvDetectorExecutor."""
        self._uv_detector.execute(action, params, component, uv)

    def execute_photo_reactor(self, action: str, params: str, component: str, photo_reactor: PhotoReactor) -> None:
        """Assigns a photo reactor action to the PhotoReactorExecutor."""
        self._photo_reactor.execute(action, params, component, photo_reactor)

    def set_bedlayout(self, bed: int, rack_layout: int) -> None:
        """Set the layout for a specific bed with the given rack_layout."""
        bed_layout = BedLayout(bed_number=bed, rack_layout=rack_layout)
        self._bed_layouts[bed] = bed_layout
        self._log_callback("SetBedLayout", f"Bed {bed} layout set with rack_layout {rack_layout}", "", "OK")
