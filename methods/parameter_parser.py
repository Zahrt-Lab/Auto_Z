# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

from __future__ import annotations

"""
This parse through parameter strings as input to a dictionary.
ex.
parameter_input = key1=value1,key2=value2
parameter_dictionary = {'key1': 'value1', 'key2': 'value2'}
"""


def parse_params(params: str | None) -> dict[str, float | str]:
    """Parse a parameter string of the form 'key1=value1,key2=value2' into a dictionary
    Parameters:
        params (str): A string of comma-separated key=value pairs. ex. 'key1=value1,key2=value2'
    Returns:
        dict: A dictionary containing the parsed key-value pairs. 
        ex. {'key1': 'value1', 'key2': 'value2'}
    """
    param_dict = {}

    # Check if params is a non-empty string
    if not params or not isinstance(params, str) or not params.strip():
        return param_dict

    # Split the input string by commas to get individual key=value pairs
    for param in params.split(","):

        # This check ensures that we have valid key = value pairs
        if "=" not in param:
            continue
        key, value = param.split("=", 1)

        key = key.strip()
        value = value.strip()

        try:
            # Converts all values (strings) to floats if possible
            param_dict[key] = float(value)
        except ValueError:
            param_dict[key] = value

    # Returns the dictionary of parsed parameters
    return param_dict
