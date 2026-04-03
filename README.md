# AUTO_ZAHRT v3.0

![Workflow diagram](docs/AutoZahrt.png)
## Overview

AUTO_ZAHRT is a comprehensive Python-based automation platform for controlling laboratory equipment including liquid handlers, pumps, valves, temperature controllers, UV-Vis detectors, and custom built devices. The purpose of this package is to be a user-friendly code for researchers to define complex experimental workflows with 

## Installation

```bash
# Install from the directory
pip install /path/to/Auto_Zahrt_v3

# Or create a distribution and install
cd Auto_Zahrt_v3
python -m build
pip install dist/auto_zahrt-3.0.0-py3-none-any.whl
```

## GUI usage

After installation, you can launch the GUI using:

```bash
auto-zahrt-gui
```

## Programmatic Usage

For more complex workflows, below is an example of how it can be integrated into more complex workflows.

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
 - Component: representing which device.
 - Action: What the specified device should be doing. 
 - Parameters: Variables 
 - Notes: Documents what each particular step is supposed to do.
 - delay: Time in seconds before running the next command.

## License

Copyright (C) 2025 by Professor Andrew Zahrt. All rights reserved.

This software is the intellectual property of Professor Andrew Zahrt.
Contributions by graduate students Scott Laverty are acknowledged.
Do not replicate or redistribute without permission.

## Contributing

This is proprietary research software. For collaboration inquiries, please contact Professor Andrew Zahrt.
