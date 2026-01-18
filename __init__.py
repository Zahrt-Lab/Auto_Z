# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
AUTO_ZAHRT v3.0
Automated laboratory instrumentation control system for chemical experiments.
"""

__version__ = "3.0.0"
__author__ = "Professor Andrew Zahrt"

# Import main classes for convenient access
from methods import GeneralExperimentMethod

__all__ = ['GeneralExperimentMethod', '__version__', '__author__']
