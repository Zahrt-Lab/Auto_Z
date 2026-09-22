# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
AUTO_Z v3.0
Automated laboratory instrumentation control system for chemical experiments.
"""

__version__ = "3.0.0"
__author__ = "Professor Andrew Zahrt"

# Import main classes for convenient access
from methods import GeneralExperimentMethod

__all__ = ['GeneralExperimentMethod', '__version__', '__author__']
