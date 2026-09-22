# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
Instrument management utilities for General Methods.
Handles loading instrument configurations and managing connections.

To add a new device: edit methods/device_registry.toml, no code changes needed.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from .registry_loader import build_instance


class InstrumentManager:
    """Manages instrument configuration, initialization, and connections."""

    def __init__(self, instrument_config_file: str, experiment_subdir: str | None = None) -> None:
        """
        Initialize the instrument manager.

        Parameters:
         - instrument_config_file: Path to the instrument configuration CSV
         - experiment_subdir: Optional subdirectory for instruments that need output paths

        Returns:
         - None
        """
        self.instrument_config_file: str = instrument_config_file
        self.experiment_subdir: str | None = experiment_subdir

        self.instruments: dict[str, Any] = (
            {}
        )  # {attr_name: device_instance} # e.g. {"Pump1": <VICI M6 Pump object>, "Pump2": <VICI M6 Pump object>)}
        self.instrument_types: dict[str, str] = (
            {}
        )  # {attr_name: InstrumentType} # e.g. {"Pump1": "Pump", "Pump2": "Pump"}

        self.instrument_config: pd.DataFrame | None = self.load_instrument_config(
            self.instrument_config_file
        )
        self.initialize_instruments(self.instrument_config)
        self.connect_all_instruments()

    def load_instrument_config(self, config_file: str) -> pd.DataFrame | None:
        """Load the instrument configuration CSV and return a DataFrame of the device configuration info."""
        try:
            config_df = pd.read_csv(config_file)
            print(f"LOADING INSTRUMENT CONFIGURATION FILE: {config_file}")
            return config_df
        except Exception as e:
            print(f"ERROR LOADING INSTRUMENT CONFIGURATION: {e}")

    def initialize_instruments(self, config_df: pd.DataFrame | None) -> None:
        """Instantiate devices from the configuration DataFrame using the device registry."""
        self.instruments = {}
        if config_df is None:
            print("ERROR: NO INSTRUMENT CONFIGURATION FILE LOADED.")
            return
        
        experiment_subdirectory = {"experiment_subdir": self.experiment_subdir}

        for _, row in config_df.iterrows():
            instrument_type = row["InstrumentType"].strip()
            # if DeviceNumber column exists and is not NaN, append it to the instrument type dictionary
            device_number = (
                str(row["DeviceNumber"]).strip()
                if not pd.isna(row["DeviceNumber"])
                else ""
            )
            # Assigned name of instrument, ex. Pump names would be Pump_1, Pump_2, etc. 
            attr_name = (
                f"{instrument_type}_{device_number}" if device_number else instrument_type
                         )

            try:
                obj = build_instance(instrument_type, row, context=experiment_subdirectory)
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

    def connect_all_instruments(self) -> None:
        """Connect to all initialized instruments that have a connect() method."""
        for name, device in self.instruments.items():
            if hasattr(device, "connect"):
                try:
                    device.connect()
                    print(f"connected to {name}")
                except Exception as e:
                    print(f"FAILED TO CONNECT TO {name}: {e}")
