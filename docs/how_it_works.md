# How Auto_Z Works

Auto_Z is a Python-based laboratory automation platform. You describe an
experiment as two CSV files — one listing your instruments, one listing the
actions to perform — and the software connects to every device over serial/USB,
executes each action in order, and writes a timestamped log of everything that
happened.

---

## The two input files

### 1. Instrument configuration CSV

Tells the software which physical devices are connected and where.

```
InstrumentType,   DeviceNumber, Name,     COMPort, OtherParams
VICI_M6_Pump,     1,            Pump,     COM17,
Temperature,      1,            TempCtrl, COM12,
DH2000,           1,            DH2000,   COM9,
```

- **InstrumentType** must match an entry in `methods/device_registry.toml`.
- **DeviceNumber** lets you have multiple devices of the same type (`Pump_1`, `Pump_2`, ...).
- The software uses `InstrumentType_DeviceNumber` as the component name you'll
  reference in the method CSV (e.g. `VICI_M6_Pump_1`).

### 2. Method CSV

A sequential list of actions. Each row is one command sent to one device.

```
Component,      Action,           Parameters,                    Notes,           delay
VICI_M6_Pump_1, aspirate,         flow_rate=100;volume=500,      Aspirate sample, 0.5
VICI_M6_Pump_1, dispense,         flow_rate=50;volume=500,       Dispense,        0.5
SYNC,           wait_for_pumps,   ,                              Wait for pumps,  0.0
Temperature_1,  set_temperature,  temp=37.5,                     Set temp,        0.5
Temperature_1,  wait_convergence, target_temp=37.5;tolerance=2,  Wait stable,     0.5
```

- **Parameters** use `key=value` pairs separated by `;`.
- **delay** is a per-row pause (in seconds) after the action completes.
- `SYNC / wait_for_pumps` is a special row that blocks until all background
  pump threads finish (see "Asynchronous pumps" below).

---

## Execution flow

When you call `GeneralExperimentMethod.run_experiment()`, this is what happens:

```
1. Load method CSV into a DataFrame
2. InstrumentManager reads the instrument config CSV
   └── For each row: look up the device class in device_registry.toml,
       instantiate it, call device.connect()
3. ExperimentLogger creates a dated output directory and opens a log CSV
4. StatusMonitor starts as a background daemon thread
   └── Polls device.status() every N seconds, watches instrument_control.txt
5. Iterate through every row in the method CSV:
   a. Check the continue flag (stops here if emergency stop was triggered)
   b. Look up the device instance by component name
   c. Determine device type (Pump, Valve, TemperatureController, ...)
   d. Route to the matching sub-executor (PumpExecutor, ValveExecutor, ...)
   e. Sub-executor parses parameters, calls the device method, logs the result
   f. Sleep for the row's delay value
6. Wait for any remaining pump threads to finish
7. Call shutdown(): safe_shutdown() on every device, close all serial ports
```

### Asynchronous pumps

Pump `aspirate` and `dispense` calls run in background threads so the UV-detector 
or PhotoReactor can move simultaneously. Insert a
`SYNC / wait_for_pumps` row wherever you need to guarantee the pumps have
finished before continuing.

---

## Key classes and where to find them

| Class | File | What it does |
|-------|------|--------------|
| `GeneralExperimentMethod` | `methods/methods.py` | Main orchestrator — ties everything together |
| `InstrumentManager` | `methods/instrument_manager.py` | Reads config, instantiates and connects all devices |
| `DeviceExecutor` | `methods/device_executors.py` | Routes each CSV row to the right sub-executor |
| `ExperimentLogger` | `methods/experiment_logger.py` | Creates output directory, writes action log CSV |
| `StatusMonitor` | `methods/status_monitor.py` | Background thread — polls status, watches control file |
| `ParameterParser` | `methods/parameter_parser.py` | Parses `key=value;key=value` parameter strings |
| `build_instance` | `methods/registry_loader.py` | Instantiates any device from `device_registry.toml` |

Each hardware category also has an abstract base class (e.g. `Pump`,
`TemperatureController`) and one or more concrete implementations in
subdirectories under `devices/`.

---

## Output files

For each run, `ExperimentLogger` creates a timestamped subdirectory under
`Experimental_Data/Outputs/YYYY_MM_DD/`. Inside you will find:

- A copy of the method CSV you ran.
- `YYYY_MM_DD_HH-MM-SS_Experimental_Log.csv` — every action with elapsed time,
  component, action, parameters, output, and notes.
- `YYYY_MM_DD_HH-MM-SS_Status_Log.csv` — periodic device status snapshots.

---

## Emergency stop

Two plain-text control files are written to their configured paths at the start of every run. If relative paths are used, they are resolved relative to the process working directory. `True`:

- `instrument_control.txt`
- `dh2000_light_source_control.txt`

To trigger an emergency stop mid-run, open `instrument_control.txt` and change
its contents to `False`. The `StatusMonitor` thread checks this file every
second and sets the stop flag. On the next loop iteration the orchestrator
calls `emergency_stop()`, which stops all devices and closes all serial ports.

---

## Adding a new device

No Python changes are needed for devices that fit an existing category
(Pump, Valve, TemperatureController, etc.).

1. Write your concrete class in a new subdirectory under `devices/`.
2. Add a block to `methods/device_registry.toml`:

```toml
[devices.MyNewPump]
import_path = "devices.industry_components.pumps.my_pump.my_pump"
class_name  = "MyNewPump"
group       = "Pump"
port_kwarg  = "port"
```

3. Reference it in your instrument config CSV as `InstrumentType = MyNewPump`.

For a completely new device category, you will also need a new abstract base
class and a matching sub-executor — follow any existing category as a template.

---

## Running the test suite

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all simulation tests (no hardware required)
pytest test/simulation -q

# Run everything including hardware tests (lab only)
pytest test/ -v
```
