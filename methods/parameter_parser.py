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
