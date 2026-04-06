# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Executor for PhotoReactor (MirrorBox365nm) actions.
Actions: set_dimmer, status, read_temperature.
"""

from devices.custom_components.light_source.light_source_base import PhotoReactor
from methods.parameter_parser import parse_params

# TODO : The PhotoReactor should be generic, but currenltly only has MirrorBox365nm implmentenation. Need to make more generic
class PhotoReactorExecutor:
    """Executes CSV method actions for PhotoReactor devices."""

    def __init__(self, log_callback):
        """
        Args:
            log_callback: Function to log an action row (component, action, params, output).
        """
        self.log_to_csv = log_callback

    def execute(self, action: str, params: str, component: str, mirror_box: PhotoReactor):
        """Route action string to the appropriate PhotoReactor method."""
        try:
            if action == "set_dimmer":
                dimmer_value = int(parse_params(params).get('value'))  
                response = mirror_box.set_dimmer(dimmer_value)
                self.log_to_csv(component, action, params, response or "OK")

            # TODO : There needs to be a more generic way to handle status and temperature reading for different photo reactors. 
            elif action == "status":
                st = mirror_box.status()
                notes = (f"L1={'ON' if st.get('light1_on') else 'OFF'} "
                         f"L2={'ON' if st.get('light2_on') else 'OFF'} "
                         f"TC3={st.get('temp_light1_c')}C "
                         f"TC4={st.get('temp_light2_c')}C")
                self.log_to_csv(component, action, params, str(st), notes=notes)

            # Needs to be a more generic way to handle temperature reading for different photo reactors.
            elif action == "read_temperature":
                temp_data = mirror_box.read_temperature_stream()
                if 'error' in temp_data:
                    self.log_to_csv(component, action, params, f"Error: {temp_data['error']}")
                else:
                    notes = (f"TC3={temp_data.get('temp_light1_c')}C "
                             f"TC4={temp_data.get('temp_light2_c')}C")
                    self.log_to_csv(component, action, params, str(temp_data), notes=notes)

            else:
                self.log_to_csv(component, action, params,
                                f"Error: Unknown PhotoReactor action '{action}'")
                raise ValueError(f"Unknown PhotoReactor action '{action}'")

        except Exception as e:
            self.log_to_csv(component, action, params, f"Error: {e}")
            raise
