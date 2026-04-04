# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Parameter parsing utilities for extracting typed values from CSV parameter strings.
Handles the conversion of comma-separated key=value pairs into Python data types.
"""

def parse_params(params):
    """Parse a parameter string of the form 'key1=value1,key2=value2' into a dict."""
    param_dict = {}
    if not params or not isinstance(params, str) or not params.strip():
        return param_dict
    for param in params.split(','):
        if '=' not in param:
            continue
        key, value = param.split('=', 1)
        key = key.strip()
        value = value.strip()
        try:
            param_dict[key] = float(value)
        except ValueError:
            param_dict[key] = value
    return param_dict

class ParameterParser:
    """Helper class for parsing parameters from CSV method files."""
    
    @staticmethod
    def extract_bed_rack_layout(params):
        """Extract bed and rack_layout from params."""
        param_dict = {key.strip(): int(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return param_dict['bed'], param_dict['rack_layout']

    @staticmethod
    def extract_bed_well(params):
        """Extract bed and well from params."""
        param_dict = {key.strip(): int(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return int(param_dict['bed']), int(param_dict['well'])

    @staticmethod
    def extract_height(params):
        """Extract height from params."""
        param_dict = {key.strip(): int(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return param_dict['height']

    @staticmethod
    def extract_flow_rate_and_volume(params):
        """Extract flow_rate and volume from params (generic, no pump_id)."""
        param_dict = {key.strip(): float(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return param_dict['flow_rate'], param_dict['volume']

    @staticmethod
    def extract_position(params):
        """Extract position from params."""
        param_dict = {key.strip(): int(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return param_dict.get('position')

    @staticmethod
    def extract_temperature_value(params):
        """Extract temperature value from params."""
        param_dict = {key.strip(): float(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return param_dict['temp']

    @staticmethod
    def extract_syringe_volume(params):
        """Extract syringe volume (mL) from params."""
        param_dict = {key.strip(): float(value.strip()) for key, value in
                      (param.split('=') for param in params.split(','))}
        return param_dict['volume_ml']

    @staticmethod
    def extract_uv_detector_parameters(params):
        """
        Extract UV detector parameters from a parameter string.
        Format: "integration_time=30000,num_scans=10,measurement_interval=5,target_wavelengths=409;509"
        target_wavelengths uses semicolons as separators (not commas) to avoid ambiguity.
        Returns a dict with parsed parameters; returns empty dict if params is empty/None.
        """
        result = {}
        if not params or not isinstance(params, str) or not params.strip():
            return result
        for param in params.split(','):
            if '=' not in param:
                continue
            key, value = param.split('=', 1)
            key = key.strip()
            value = value.strip()
            if key == 'target_wavelengths':
                result[key] = [float(wl) for wl in value.split(';') if wl.strip()]
            else:
                try:
                    result[key] = float(value)
                except ValueError:
                    result[key] = value
        return result
