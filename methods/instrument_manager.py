# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Instrument management utilities for AUTO_ZAHRT.
Handles loading configuration, initializing instruments, and managing connections.

To add a new device: edit methods/device_registry.toml — no changes needed here.
"""

import pandas as pd

from .registry_loader import build_instance


class InstrumentManager:
    """Manages instrument configuration, initialization, and connections."""

    def __init__(self, instrument_config_file, experiment_subdir=None):
        """
        Initialize the instrument manager.

        Args:
            instrument_config_file: Path to the instrument configuration CSV
            experiment_subdir: Optional subdirectory for instruments that need output paths
        """
        self.instrument_config_file = instrument_config_file
        self.experiment_subdir = experiment_subdir

        self.instruments = {}       # {attr_name: device_instance}
        self.instrument_types = {}  # {attr_name: InstrumentType}

        self.instrument_config = self.load_instrument_config(self.instrument_config_file)
        self.initialize_instruments(self.instrument_config)
        self.connect_all_instruments()

    def load_instrument_config(self, config_file):
        """Load the instrument configuration CSV and return a DataFrame."""
        try:
            config_df = pd.read_csv(config_file)
            print(f"Loaded instrument configuration from {config_file}")
            return config_df
        except Exception as e:
            print(f"Error loading instrument configuration: {e}")
            return None

    def initialize_instruments(self, config_df):
        """Instantiate devices from the configuration DataFrame using the device registry."""
        self.instruments = {}
        if config_df is None:
            print("No instrument configuration available.")
            return

        context = {"experiment_subdir": self.experiment_subdir}

        for _, row in config_df.iterrows():
            instrument_type = row["InstrumentType"].strip()
            device_number = str(row["DeviceNumber"]).strip() if not pd.isna(row["DeviceNumber"]) else ""
            attr_name = f"{instrument_type}_{device_number}" if device_number else instrument_type

            try:
                obj = build_instance(instrument_type, row, context=context)
            except ValueError as e:
                print(f"Skipping unknown instrument type: {e}")
                continue
            except Exception as e:
                print(f"Error initializing {instrument_type}: {e}")
                continue

            self.instruments[attr_name] = obj
            self.instrument_types[attr_name] = instrument_type
            com_port = row.get("COMPort", "N/A")
            print(f"Initialized {attr_name} ({instrument_type}) on {com_port}")

    def connect_all_instruments(self):
        """Connect to all initialized instruments that have a connect() method."""
        for name, device in self.instruments.items():
            if hasattr(device, "connect"):
                try:
                    device.connect()
                    print(f"Connected to {name}")
                except Exception as e:
                    print(f"Failed to connect to {name}: {e}")