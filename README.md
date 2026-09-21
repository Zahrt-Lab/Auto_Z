# Auto-Z

Auto-Z is a Python-based laboratory automation framework developed by the
Zahrt Lab for controlling and coordinating laboratory instrumentation.

The platform uses instrument-configuration and experimental-method CSV files
to define automated experiments. During execution, Auto-Z initializes the
specified hardware, dispatches experimental commands, monitors instrument
status, and records experimental and status logs.

Auto-Z was developed to support automated and autonomous chemistry workflows,
including the continuous-flow photochemistry platform described in our
associated manuscript.

## Documentation

Detailed documentation is available in the `docs/` directory:

- [`how_it_works.md`](docs/how_it_works.md) — overview of the software
  architecture, experimental workflow, input files, logging, device registry,
  and instrument control.
- [`usb_port_identification.md`](docs/usb_port_identification.md) — notes and
  proposed approach for robust USB instrument identification using VID/PID
  and physical USB-port information.

## Installation

Auto-Z requires Python 3.9 or later.

Clone the repository:

```bash
git clone https://github.com/Zahrt-Lab/Auto_Z.git
cd Auto_Z


Create and activate a virtual environment, then install the package:

```bash
pip install -e .
```

For development and testing:

```bash
pip install -e ".[dev]"
```

The package dependencies are defined in `pyproject.toml`. A pinned
`requirements.txt` is also provided to document the software environment used
during development and experimental work.

## Usage

Experiments are defined using two CSV files:

1. An **instrument configuration file**, which specifies the instruments and
   their communication settings.
2. A **method file**, which specifies the sequence of experimental commands.

Auto-Z can then execute the method through the laboratory-control framework and
write timestamped experimental and status logs.

For a detailed description of this workflow, see
[`docs/how_it_works.md`](docs/how_it_works.md).

The graphical interface can be launched after installation with:

```bash
auto-gui
```

## Testing

Simulation tests that do not require physical laboratory hardware can be run
with:

```bash
pytest test/simulation -q
```

Pump timing tests that depend on real elapsed-time behavior are excluded from
the default simulation test suite. Hardware tests require the corresponding
laboratory instruments and should only be run on an appropriately configured
system.

## Manuscript Data and Optimization Code

Auto-Z provides the laboratory hardware-control and experiment-execution
framework.

The experiment-specific Bayesian optimization workflow, methods, experimental
data, and analysis associated with the manuscript are maintained separately in
the `dead_mans_fingers` repository.

[dead_mans_fingers](https://github.com/Zahrt-Lab/dead_mans_fingers)

## Platform-Specific Dependencies

Some instrument drivers require vendor software or hardware-specific libraries
that are not distributed through PyPI. In particular, Ocean Optics
spectrometers require the appropriate OceanDirect installation, and some
instrument communication interfaces may require vendor-provided Windows
libraries.

These dependencies are only required when using the corresponding hardware.

## Citation

Citation information will be added with the publication release.

## License

License information is provided in [`LICENSE`](LICENSE).
he publication release.
License
License information is provided in LICENSE.