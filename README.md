# AUTO_ZAHRT v3.0

Automated laboratory instrumentation control system for chemical experiments.
![Workflow diagram](docs/AutoZahrt.png)
## Overview

AUTO_ZAHRT is a comprehensive Python-based automation platform for controlling laboratory equipment including liquid handlers, pumps, valves, temperature controllers, and UV-Vis detectors. The system enables researchers to define complex experimental workflows through CSV-based method files and execute them with precise control and monitoring.

## Features

- **Modular Architecture**: Clean separation of concerns with dedicated modules for different instrument types
- **CSV-Based Methods**: Define experimental sequences using human-readable CSV files
- **Real-time Monitoring**: Background status monitoring with control file integration
- **Multiple Instrument Support**:
  - Liquid Handlers (GX281, Ender3)
  - Pumps (VICI M6, Isametic, Tricontinental)
  - Syringe Pumps (PHD Ultra)
  - Valves (VICI)
  - Temperature Controllers (TC720)
  - UV-Vis Detectors (Ocean Optics, DH2000)
- **GUI Interface**: User-friendly Tkinter-based interface for experiment control
- **Comprehensive Logging**: Automatic CSV logging of all experimental actions

## Installation

### From Source (Development)

```bash
# Clone or navigate to the repository
cd Auto_Zahrt_v3

# Install in editable mode with development dependencies
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### As a Package

```bash
# Install from the directory
pip install /path/to/Auto_Zahrt_v3

# Or create a distribution and install
cd Auto_Zahrt_v3
python -m build
pip install dist/auto_zahrt-3.0.0-py3-none-any.whl
```

### Requirements

- Python 3.9 or higher
- pandas >= 2.0.0
- pyserial >= 3.5

## Usage

### Launch the GUI

After installation, you can launch the GUI using:

```bash
auto-zahrt-gui
```

Or from Python:

```python
from methods.methods_gui import main
main()
```

### Programmatic Usage

```python
from methods import GeneralExperimentMethod

# Initialize experiment
experiment = GeneralExperimentMethod(
    input_file="path/to/method.csv",
    instrument_config_file="path/to/instruments.csv",
    output_dir="Experimental_Data/Outputs"
)

# Run experiment
experiment.run_experiment()
```

## Project Structure

```
Auto_Zahrt_v3/
├── components/           # Hardware component drivers
├── liquid_handlers/      # Liquid handler implementations
├── methods/             # Core experiment method classes
│   ├── methods.py              # Main experiment orchestrator
│   ├── parameter_parser.py    # CSV parameter parsing
│   ├── experiment_logger.py   # Logging and file management
│   ├── status_monitor.py      # Background monitoring
│   ├── instrument_manager.py  # Device initialization
│   └── device_executors.py    # Action execution
├── pumps/               # Pump drivers
├── syringe_pumps/       # Syringe pump drivers
├── temperature_controller/ # Temperature control
├── uv_detectors/        # UV-Vis detector drivers
├── valves/              # Valve controllers
├── utils/               # Utility modules
└── Experimental_Data/   # Output directory

```

## Configuration

### Instrument Configuration CSV

Define your instruments in a CSV file:

```csv
Component,Type,Port,Additional_Params
GX281,GX281,COM3,
Pump1,VICI_M6,COM4,
Valve1,VICI_Valve,COM5,position=1
```

### Method CSV

Define your experimental sequence:

```csv
Component,Action,Parameters,Notes,delay
GX281,set_bedlayout,bed=1;rack_layout=1,Setting up bed,0.5
Pump1,aspirate,flow_rate=100;volume=500,Aspirate sample,0.5
```

## Control Files

The system uses control files for runtime experiment management:

- `instrument_control.txt`: Set to "False" to stop the experiment
- `dh2000_light_source_control.txt`: Control DH2000 light source behavior

## Development

### Running Tests

```bash
pytest
```

### Code Organization

The refactored v3.0 architecture follows clean separation of concerns:

- **Parameter Parsing** (`parameter_parser.py`): Centralized CSV parameter extraction
- **Logging** (`experiment_logger.py`): All file I/O and CSV logging
- **Monitoring** (`status_monitor.py`): Background instrument status polling
- **Instrument Management** (`instrument_manager.py`): Device initialization and connection
- **Device Execution** (`device_executors.py`): Action execution for all device types
- **Orchestration** (`methods.py`): High-level experiment coordination

## License

Copyright (C) 2025 by Professor Andrew Zahrt. All rights reserved.

This software is the intellectual property of Professor Andrew Zahrt.
Contributions by graduate students Scott Laverty are acknowledged.
Do not replicate or redistribute without permission.

## Contributing

This is proprietary research software. For collaboration inquiries, please contact Professor Andrew Zahrt.
