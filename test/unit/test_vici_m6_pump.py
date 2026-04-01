# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Unit tests for TC720 temperature controller — pure logic, no real serial hardware.
A MagicMock is attached directly to tc.ser; GeneralExperimentMethod is never involved.
"""
'''
import pytest
from unittest.mock import patch

from pumps.vici_m6_pump.vici_m6_pump import VICI_M6_Pumps
from conftest import make_vici_m6_response, make_vici_m6_device

# ---------------------------------------------------------------------------
# initialize parameters
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Connect
# ---------------------------------------------------------------------------

#---------------------------------------------------------------------------
# set_flow_rate
#---------------------------------------------------------------------------
'''
