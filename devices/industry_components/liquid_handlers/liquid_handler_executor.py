# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Executor for liquid handler actions.
Handles move_xy, move_z, move_z_height, move_home, and set_bedlayout.
"""

from __future__ import annotations

import time
from typing import Callable

from devices.industry_components.liquid_handlers.bed_layout import BedLayout
from devices.industry_components.liquid_handlers.liquid_handlers import LiquidHandler

LogCallback = Callable[[str, str, str, str, str], None]


class LiquidHandlerExecutor:
    """Executes CSV method actions for liquid handler devices."""

    def __init__(self, bed_layouts: dict[int, BedLayout], log_callback: LogCallback) -> None:
        """
        Parameters:
            bed_layouts: Shared dict of {bed_number: BedLayout} managed by the experiment.
            log_callback: Function to log an action row (component, action, params, output).
        """
        self.bed_layouts = bed_layouts
        self.log_to_csv = log_callback

    def execute(
        self, action: str, params: str, component: str, liquid_handler: LiquidHandler
    ) -> None:
        """Route action string to the appropriate liquid handler method."""
        from methods.parameter_parser import parse_params

        if action == "set_bedlayout":
            bed = parse_params(params).get("bed")
            rack_layout = parse_params(params).get("rack_layout")
            if hasattr(liquid_handler, "set_bedlayout"):
                liquid_handler.set_bedlayout(bed, rack_layout)
            self.log_to_csv(
                component,
                action,
                params,
                f"Setting bed {bed} to bed layout {rack_layout}",
            )

        elif action == "move_home":
            liquid_handler.home()
            self.log_to_csv(component, action, "", "Homing liquid handler")

        elif action == "move_z_height":
            z_coord = parse_params(params).get("height")
            liquid_handler.move_z(z_coord)
            self.log_to_csv(
                component, action, params, f"Moving needle to z height {z_coord}"
            )

        elif action == "move_xy":
            bed = parse_params(params).get("bed")
            well = parse_params(params).get("well")

            # Move needle to safe height before XY movement to avoid collisions
            safe_z = liquid_handler.get_safe_z_height()
            liquid_handler.move_z(safe_z)
            time.sleep(1)
            self.log_to_csv(
                component,
                action,
                params,
                f"Moving liquid handler needle up before XY move: z={safe_z}",
            )

            if hasattr(liquid_handler, "move_to_well"):
                liquid_handler.move_to_well(bed, well)
            else:
                x = self.bed_layouts[bed].get_well(well).get_x()
                y = self.bed_layouts[bed].get_well(well).get_y()
                liquid_handler.move_xy(x, y)
            self.log_to_csv(
                component,
                action,
                params,
                f"Moving liquid handler to bed {bed} well {well}",
            )

        elif action == "move_z":
            bed = parse_params(params).get("bed")
            well = parse_params(params).get("well")

            if hasattr(liquid_handler, "get_well_z"):
                z = liquid_handler.get_well_z(bed, well)
            else:
                z = self.bed_layouts[bed].get_well(well).get_z()
            liquid_handler.move_z(z)
            self.log_to_csv(
                component,
                action,
                params,
                f"Moving liquid handler needle on bed {bed} well {well}: z={z}",
            )

        else:
            self.log_to_csv(
                component,
                action,
                params,
                f"Error: Unknown action '{action}' for liquid handler",
            )
