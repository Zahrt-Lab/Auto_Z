# Auto_Zahrt v3 — Claude Code Context

## Project Purpose
Python-based laboratory automation platform for controlling chemical experiment hardware (pumps, valves, liquid handlers, temperature controllers, UV detectors) via serial/USB connections. Experiments are defined as CSV method files and executed by a central orchestration class.

- **Version:** 3.0.0
- **Python:** 3.9+
- **Entry point:** `auto-zahrt-gui` (console script → `methods.methods_gui:main`)

---

## Architecture Overview

### Core Orchestration (`methods/`)
| File | Class | Responsibility |
|------|-------|----------------|
| `methods.py` | `GeneralExperimentMethod` | Main orchestrator — loads method CSV, runs experiment loop, safe shutdown |
| `instrument_manager.py` | `InstrumentManager` | Reads instrument config CSV, instantiates and connects all devices |
| `device_executors.py` | `DeviceExecutor` | Routes each CSV action row to the correct device method |
| `experiment_logger.py` | `ExperimentLogger` | Creates dated output directories, writes action and status CSV logs |
| `status_monitor.py` | `StatusMonitor` | Background daemon thread — polls device status, watches control files |
| `parameter_parser.py` | `ParameterParser` | Parses `key=value;key=value` strings from CSV parameter cells (static methods) |
| `methods_gui.py` | `MethodsEditorWindow` | Tkinter GUI — edit configs, run experiments, view results (986 lines) |

### Hardware Modules
Each hardware category follows the same pattern: **abstract base class** in the category root + **concrete implementation** in a subdirectory.

| Category | Abstract Base | Concrete Implementations |
|----------|--------------|--------------------------|
| Liquid Handlers | `liquid_handlers/liquid_handlers.py` | `gx281/` (Windows DLL), `ender3_liquid_handler/` |
| Pumps | `pumps/pumps.py` | `vici_m6_pump/`, `isametic_pump/`, `tricontinental_c24000/`, `ismatec_Regio_ICC/` |
| Syringe Pumps | `syringe_pumps/syringe_pumps.py` | `phd_ultra/`, `phd_ultra_pumps/` |
| Valves | `valves/valves.py` | `vici_valves/` (6/10/24-way) |
| Temperature Controllers | `temperature_controller/temperature_controller.py` | `tc720/` |
| UV Detectors | `uv_detectors/uv_detector.py` | Ocean Optics HR2000, `dh2000.py` light source |
| Custom | `custom_components/light_source/mirror_box_365nm/` | MirrorBox365nm (365nm UV with dimmer) |

### Execution Flow
```
Method CSV → GeneralExperimentMethod.run_experiment()
    → InstrumentManager  — instantiates and connects all devices
    → DeviceExecutor     — dispatches each CSV row to the right device method
    → ExperimentLogger   — logs each action with timestamp/elapsed time
    → StatusMonitor thread — polls device.status() at regular intervals
    → Safe shutdown      — DH2000 shutter close, MirrorBox dimmer off, serial ports closed
```

Pump `aspirate`/`dispense` calls are **asynchronous** (spawned as threads). Use `SYNC, wait_for_pumps` in the method CSV to block until all pump threads finish.

---

## CSV Formats

### Instrument Configuration CSV
```
InstrumentType, DeviceNumber, Name, COMPort, OtherParams
GX281,          1,            GX-281,   COM2,
VICI_M6_Pump,   1,            Pump,     COM17,
Temperature,    1,            TempCtrl, COM12,
DH2000,         1,            DH2000,   COM9,
```

### Method CSV
```
Component, Action,           Parameters,                                    Notes,              delay
GX281,     set_bedlayout,    bed=1;rack_layout=1,                          Setting up bed,     0.5
GX281,     move_xy,          bed=1;well=1,                                 Move to well,       0.5
Pump,      aspirate,         flow_rate=100;volume=500,                     Aspirate sample,    0.5
Pump,      dispense,         flow_rate=50;volume=500,                      Dispense,           0.5
SYNC,      wait_for_pumps,   ,                                             Wait for async,     0.5
TempCtrl,  set_temperature,  temp=37.5,                                    Set temperature,    0.5
TempCtrl,  wait_convergence, target_temp=37.5;tolerance=2;duration=120,   Wait stable,        0.5
```

Parameter strings use `key=value` pairs separated by `;`. UV detector wavelengths also use `;` as separator within the parameter string.

---

## Control Files (Runtime Signals)
Written to the experiment output directory during a run:

- **`instrument_control.txt`** — set to `"False"` to trigger an emergency stop; `StatusMonitor` checks this every second and sets the continue flag to False
- **`dh2000_light_source_control.txt`** — controls whether DH2000 performs a safe shutdown (shutter close + lamps off) when the experiment ends or errors

---

## Adding New Hardware
Follow this 5-step pattern (see any existing hardware module for reference):

1. Create the abstract base class in the category root (e.g., `new_device/new_device.py`)
2. Create the concrete implementation in a subdirectory
3. Register the new type in `methods/instrument_manager.py` → `initialize_instruments()`
4. Add an executor method to `methods/device_executors.py`
5. Add a GUI widget/row to `methods/methods_gui.py`

---

## Testing

### Structure
```
test/
├── conftest.py          # pytest fixtures and configuration
├── unit/                # Pure logic tests — parsing, config (run in CI)
├── integration/         # Serial/methods tests with mocks (run in CI)
└── hardware/            # Real hardware required (excluded from CI)
```

### Markers
```python
@pytest.mark.hardware       # Requires physical hardware connected
@pytest.mark.mirror_box     # MirrorBox365nm specific
@pytest.mark.tc720          # TC720 temperature controller specific
```

### Running Tests
```bash
# CI subset (no hardware)
pytest test/unit/ test/integration/ -v

# All tests including hardware (lab only)
pytest test/ -v

# With coverage
pytest test/unit/ test/integration/ --cov
```

---

## CI/CD (`.github/workflows/ci.yml`)
- **Platform:** Ubuntu latest
- **Python:** 3.9
- **Triggers:** push to any branch + daily schedule (6 AM UTC)
- **Command:** `pip install -e ".[dev]"` then `pytest test/unit/ test/integration/ -v`
- Hardware tests are **never** run in CI

---

## Key Dependencies
| Package | Version | Use |
|---------|---------|-----|
| `pandas` | ≥2.0.0 | CSV reading/manipulation |
| `pyserial` | ≥3.5 | Serial device communication |
| `matplotlib` | ≥3.5.0 | Plotting (UV data, status monitor) |
| `numpy` | ≥1.23.0 | Numerical operations |

**Optional (not pip-installable):**
- Ocean Optics OceanDirectAPI Python SDK — USB spectrometer
- `gsioc32.dll` (Windows) — GX281 liquid handler control

---

## Key Files Quick Reference
| Purpose | File |
|---------|------|
| Main orchestration logic | `methods/methods.py` |
| Add/modify device actions | `methods/device_executors.py` |
| Register new device types | `methods/instrument_manager.py` |
| Add CSV parameter formats | `methods/parameter_parser.py` |
| GUI (largest file) | `methods/methods_gui.py` |
| Package config / deps | `pyproject.toml`, `requirements.txt` |
