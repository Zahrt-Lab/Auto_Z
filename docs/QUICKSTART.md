# AUTO_ZAHRT Quick Start Guide

## Installation

### Option 1: Development Installation (Recommended for active development)

```bash
cd /path/to/Auto_Zahrt_v3
pip install -e .
```

This installs the package in "editable" mode - changes to the source code take effect immediately without reinstalling.

### Option 2: Standard Installation

```bash
pip install /path/to/Auto_Zahrt_v3
```

### Option 3: Install from Wheel (for distribution)

```bash
# First, build the wheel
cd /path/to/Auto_Zahrt_v3
python -m build

# Then install
pip install dist/auto_zahrt-3.0.0-py3-none-any.whl
```

## Verify Installation

```bash
python verify_install.py
```

Expected output:
```
✓ Core module imported successfully
✓ Parameter parser imported
✓ Experiment logger imported
✓ Status monitor imported
✓ Instrument manager imported
✓ Device executors imported
✓ pandas 2.3.1
✓ pyserial 3.5

✅ AUTO_ZAHRT installation verified successfully!
```

## Using AUTO_ZAHRT

### Launch GUI

After installation, launch the GUI with:

```bash
auto-zahrt-gui
```

### Python API

```python
# Import the main class
from methods import GeneralExperimentMethod

# Create an experiment instance
experiment = GeneralExperimentMethod(
    input_file="path/to/method.csv",
    instrument_config_file="path/to/instruments.csv",
    output_dir="Experimental_Data/Outputs"
)

# Connect to instruments
experiment.instrument_manager.connect_all_instruments()

# Run the experiment
experiment.run_experiment()
```

### Import Individual Modules

```python
# Import specific components
from methods.parameter_parser import ParameterParser
from methods.experiment_logger import ExperimentLogger
from methods.instrument_manager import InstrumentManager

# Use individual liquid handlers
from liquid_handlers.gx281.gx281 import GX281
from liquid_handlers.ender3_liquid_handler.ender3_liquid_handler import Ender3

# Use pumps
from pumps.vici_m6_pump.vici_m6_pump import VICI_M6
from pumps.isametic_pump.isametic_pump import Isametic

# Use valves
from valves.vici_valves.vici_valves import VICI_Valve

# Use temperature controllers
from temperature_controller.tc720.tc720 import TC720

# Use UV detectors
from uv_detectors.dh2000 import DH2000LightSource
from uv_detectors.uv_detector import Ocean_Optics_UV_vis  # Requires OceanDirect SDK
```

## Creating Method Files

Method files are CSV files with the following columns:

- **Component**: Name of the instrument (must match instrument config)
- **Action**: Action to perform (aspirate, dispense, move_xy, etc.)
- **Parameters**: Comma-separated key=value pairs
- **Notes**: Human-readable description
- **delay**: Seconds to wait after action (optional)

Example:

```csv
Component,Action,Parameters,Notes,delay
GX281,set_bedlayout,bed=1;rack_layout=1,Configure bed layout,0.5
GX281,move_home,,Home the liquid handler,1.0
GX281,move_xy,bed=1;well=1,Move to well A1,0.5
Pump1,aspirate,flow_rate=100;volume=500,Aspirate 500 µL,0.5
```

## Creating Instrument Configuration

Instrument configuration files are CSV files specifying connected devices:

```csv
Component,Type,Port,Additional_Params
GX281,GX281,COM3,
Ender3,Ender3,COM4,
Pump1,VICI_M6,COM5,
Valve1,VICI_Valve,COM6,position=1
TC720_1,TC720,COM7,
```

## Troubleshooting

### Import Errors

If you get import errors, make sure you're in the correct environment:

```bash
# Check Python version (should be 3.9+)
python --version

# Check installed packages
pip list | grep auto-zahrt
```

### OceanDirect SDK Warning

If you see "Warning: OceanDirect SDK not found", this is normal if:
- You're on Linux (SDK is Windows-only)
- You don't have Ocean Optics hardware
- The SDK isn't installed

Other UV detector functionality (DH2000) will still work.

### Serial Port Access

On Linux, you may need to add your user to the dialout group:

```bash
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect
```

## Uninstallation

```bash
pip uninstall auto-zahrt
```

## Development

### Running Tests (when available)

```bash
pip install -e ".[dev]"
pytest
```

### Code Structure

- `methods/` - Core experiment orchestration
- `components/` - Low-level hardware drivers
- `liquid_handlers/` - Liquid handler implementations
- `pumps/` - Pump drivers
- `valves/` - Valve controllers
- `temperature_controller/` - Temperature control
- `uv_detectors/` - UV-Vis detectors
- `syringe_pumps/` - Syringe pump drivers
- `utils/` - Utility modules

## Support

For issues or questions, contact Professor Andrew Zahrt.
