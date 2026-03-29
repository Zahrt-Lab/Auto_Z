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
"""

import pandas as pd

# Import concrete implementations
from liquid_handlers.gx281.gx281 import GX281
from liquid_handlers.ender3_liquid_handler.ender3_liquid_handler import Ender3LiquidHandler
from pumps.vici_m6_pump.vici_m6_pump import VICI_M6_Pumps
from pumps.isametic_pump.isametic_pump import IsmaticPump
from pumps.tricontinental_c24000.tricontinental_c24000 import TricontinentalC24000
from syringe_pumps.phd_ultra_pumps.phd_ultra_pumps import PhdUltraPump
from valves.vici_valves.vici_valves import ViciValve
from temperature_controller.tc720.tc720 import TC720
from uv_detectors.dh2000 import DH2000LightSource
from uv_detectors.uv_detector import Ocean_Optics_UV_vis
from custom_components.light_source.mirror_box_365nm.mirror_box_365nm import MirrorBox365nm


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
        
        # Track instruments by name and type
        self.instruments = {}  # {attr_name: device_instance}
        self.instrument_types = {}  # {attr_name: InstrumentType}
        
        # Load and initialize instruments
        self.instrument_config = self.load_instrument_config(self.instrument_config_file)
        self.initialize_instruments(self.instrument_config)
        self.connect_all_instruments()
    
    def load_instrument_config(self, config_file):
        """
        Loads the instrument configuration CSV and returns a DataFrame.
        The CSV should contain columns such as InstrumentType, DeviceNumber, Name, COMPort, OtherParams.
        """
        try:
            config_df = pd.read_csv(config_file)
            print(f"Loaded instrument configuration from {config_file}")
            return config_df
        except Exception as e:
            print(f"Error loading instrument configuration: {e}")
            return None

    def initialize_instruments(self, config_df):
        """
        Initializes instrument objects based on the configuration DataFrame.
        The instruments are stored in self.instruments and also set as attributes on self.
        """
        self.instruments = {}
        if config_df is None:
            print("No instrument configuration available.")
            return

        # Loop through each instrument defined in the config file
        for _, row in config_df.iterrows():
            instrument_type = row['InstrumentType'].strip()
            device_number = str(row['DeviceNumber']).strip() if not pd.isna(row['DeviceNumber']) else ""
            com_port = row['COMPort'].strip() if not pd.isna(row['COMPort']) else None
            # Use the provided output_dir for instruments that need it (e.g., UV detector)
            other_params = row['OtherParams'] if 'OtherParams' in row else None

            # Create a unique attribute name for the instrument (e.g., "GX281_1", "Pump_1")
            attr_name = f"{instrument_type}_{device_number}" if device_number else instrument_type

            # Instantiate the instrument based on its type
            if instrument_type == "GX281":
                obj = GX281(name=attr_name)
            elif instrument_type == "Ender3_Liquid_Handler":
                obj = Ender3LiquidHandler(port=com_port, name=attr_name)
            elif instrument_type == "VICI_M6_Pump":
                # VICI_M6_Pumps __init__ does not accept a 'name' kwarg; pass port only
                obj = VICI_M6_Pumps(port=com_port)
                # Attach a friendly name attribute for consistency with other instruments
                try:
                    obj.name = attr_name
                except Exception:
                    pass
            elif instrument_type == "Isametic":
                obj = IsmaticPump(port=com_port, name=attr_name)
            elif instrument_type == "Tricontinental_C24000":
                obj = TricontinentalC24000(port=com_port, name=attr_name)
            elif instrument_type == "PhdUltraPump":
                obj = PhdUltraPump(port=com_port, name=attr_name)
            # TODO current code only supports Vici valves, add other valve types as needed and make necessary changes to code
            elif instrument_type in ("Valve6Way", "Valve10Way", "Valve24Way"):
                # pick the right string for ViciValve
                valve_type = {
                    "Valve6Way": "6-way",
                    "Valve10Way": "10-way",
                    "Valve24Way": "24-way"
                }[instrument_type]
                # ViciValve __init__ does not accept a 'name' kwarg
                obj = ViciValve(port=com_port, valve_type=valve_type)
                # Attach a friendly name attribute for consistency with other instruments
                try:
                    obj.name = attr_name
                except Exception:
                    pass
            elif instrument_type == "Temperature":
                obj = TC720(port=com_port, name=attr_name)
            elif instrument_type == "DH2000":
                obj = DH2000LightSource(port=com_port, baudrate=9600, timeout=2.0, retries=10)
                try:
                    obj.name = attr_name
                except Exception:
                    pass
            elif instrument_type == "MirrorBox365nm":
                obj = MirrorBox365nm(port=com_port, baudrate=9600, timeout=2.0)
                try:
                    obj.name = attr_name
                except Exception:
                    pass
            elif instrument_type == "OceanOptics_UVVis":
                # COM port ignored (USB auto-detect)
                # IMPORTANT: pass experiment_subdir/output dir so outputs land in the run folder
                obj = Ocean_Optics_UV_vis(
                    output_dir=self.experiment_subdir,
                    integration_time=100000,
                    num_scans=10,
                    target_wavelengths=[409.0],
                    save_file_path="UV_detection.csv",
                    measurement_interval=20.0,
                )
                try:
                    obj.name = attr_name
                except Exception:
                    pass
            else:
                print(f"Unknown instrument type: {instrument_type}")
                continue

            # Store the instrument and its type
            self.instruments[attr_name] = obj
            self.instrument_types[attr_name] = instrument_type
            print(f"Initialized {attr_name} ({instrument_type}) on COM Port {com_port if com_port else 'N/A'}")

    def connect_all_instruments(self):
        """Connect to all initialized instruments that have a connect() method."""
        for name, device in self.instruments.items():
            if hasattr(device, 'connect'):
                try:
                    device.connect()
                    print(f"Connected to {name}")
                except Exception as e:
                    print(f"Failed to connect to {name}: {e}")
