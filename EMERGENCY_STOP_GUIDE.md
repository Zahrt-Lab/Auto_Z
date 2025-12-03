# Emergency Stop Control System - Usage Guide

## Overview
The experiment control system allows you to stop a running experiment by modifying a control file.

## How It Works

### 1. Control File Location
Default: `control.txt` in the project root directory (`/home/scott/PycharmProjects/AUTO_ZAHRT_V2/`)

You can specify a custom path when creating the GeneralExperimentMethod:
```python
method = GeneralExperimentMethod(
    input_file="method.csv",
    instrument_config_file="config.csv",
    control_file="/path/to/your/control.txt"  # Custom path
)
```

### 2. Control File Contents
- **To continue experiment**: File should contain `True` (case-insensitive)
- **To stop experiment**: Change file contents to `False` (case-insensitive)

Example:
```bash
# Continue experiment
echo "True" > control.txt

# Stop experiment immediately
echo "False" > control.txt
```

### 3. Monitoring Frequency
- The control file is checked every **60 seconds** by the status monitoring thread
- Same interval as the device status monitoring

### 4. Stop Behavior
When `False` is detected:
1. Status monitor logs the stop signal
2. Main experiment loop detects `_continue_experiment = False` 
3. **Immediate stop** - current action is interrupted
4. `emergency_stop()` is called:
   - Calls `stop()` method on all connected devices
   - Closes all serial connections
   - Logs all stop events with timestamps
5. Experiment exits cleanly

### 5. Logging
All stop events are logged:
- Stop signal detection logged in main experiment CSV
- Each device stop logged individually
- Timestamps included for all events

## Example Usage

### Starting an Experiment
```python
from methods.methods import GeneralExperimentMethod

# Create experiment (control.txt will be created with "True" by default)
exp = GeneralExperimentMethod(
    input_file="my_method.csv",
    instrument_config_file="instruments.csv"
)

# Run experiment
exp.run_experiment()
```

### Stopping During Execution
While the experiment is running, from another terminal or script:
```bash
# Stop the experiment
echo "False" > control.txt
```

Within 60 seconds, the experiment will:
- Detect the stop signal
- Stop all devices
- Close all connections
- Exit cleanly

### Future Extensions
You can create multiple functions that write to the control file:

```python
def emergency_stop_button():
    """Called by GUI emergency stop button"""
    with open('control.txt', 'w') as f:
        f.write('False')

def temperature_safety_stop(current_temp, max_temp):
    """Stop if temperature exceeds limit"""
    if current_temp > max_temp:
        with open('control.txt', 'w') as f:
            f.write('False')
        print(f"SAFETY STOP: Temperature {current_temp}°C exceeds {max_temp}°C")

def pressure_safety_stop(current_pressure, max_pressure):
    """Stop if pressure exceeds limit"""
    if current_pressure > max_pressure:
        with open('control.txt', 'w') as f:
            f.write('False')
        print(f"SAFETY STOP: Pressure {current_pressure} exceeds {max_pressure}")
```

## Technical Details

### New Attributes
- `self.control_file`: Path to control file (default: "control.txt")
- `self._continue_experiment`: Boolean flag tracking experiment state

### New Methods
- `_check_continue_flag()`: Reads control file and returns True/False
- `emergency_stop()`: Stops all devices and closes connections

### Modified Methods
- `__init__()`: Added `control_file` parameter
- `_status_monitor_worker()`: Checks control file every cycle
- `run_experiment()`: Checks flag before each method step

### Thread Safety
- `_continue_experiment` flag is set by status monitor thread
- Read by main experiment thread
- No race conditions - worst case is 1 extra step before stop

## Default Behavior
- If control file doesn't exist: experiment continues
- If control file has invalid content: experiment continues
- On file read error: experiment continues (logged as warning)
- This ensures the system fails "safe" - continues rather than crashes
