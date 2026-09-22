# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
Test the parameters parser utility for converting CSV parameter strings into Python dictionaries.
"""

import pytest

from methods.parameter_parser import parse_params


@pytest.mark.parametrize("input_str, expected_output", [
    ("flow_rate=100,volume=500", {"flow_rate": 100.0, "volume": 500.0}),
    ("temp=25.5", {"temp": 25.5}),
    ("set_position=3", {"set_position": 3.0}),
    ("Bed=1,Rack Layout=204", {"Bed": 1.0, "Rack Layout": 204.0}),
    ("", {}),
])
def test_valid_parse_params(input_str, expected_output):
    """Test that valid parameter strings are parsed correctly."""
    assert parse_params(input_str) == expected_output

@pytest.mark.parametrize("input_str, expected_output", [
    ("Flow_rate=flow", {"Flow_rate": "flow"}),
    ("Bed=1Rack Layout=204", {"Bed": "1Rack Layout=204"}),   # no comma → one token, parsed as key=value
    ({"Flow_rate" : 32}, {}),                                 # dict input → not a string, returns {}
    ({}, {}),
    (None, {})
    ])                                            # None input → not a string, returns {}
def test_invalid_parse_params(input_str, expected_output):
    """Test that invalid parameter strings are handled gracefully."""
    assert parse_params(input_str) == expected_output