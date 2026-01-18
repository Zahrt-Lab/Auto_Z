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
        This method extracts UV detector parameters from a parameter string.
        The expected format is a comma-separated list of key=value pairs.
        For example: "integration_time=30000,num_scans=10,measurement_interval=5,target_wavelengths=409,509"
        Returns a dictionary with the parsed parameters.
        """
        param_dict = {key.strip(): float(value.strip()) for key, value in
            (param.split('=') for param in params.split(','))}
        return param_dict['integration_time'], \
               param_dict['num_scans'], \
               param_dict['measurement_interval'], \
               [float(wl) for wl in param_dict['target_wavelengths'].split(';')]
