# AUTO_ZAHRT Developer Guide

## Overview

This guide is for advanced users who want to add new equipment to AUTO_ZAHRT. The system uses an abstract base class architecture that ensures all devices follow consistent interfaces.

## Architecture Summary

AUTO_ZAHRT uses a **composition-based** architecture with clear separation:

- **Abstract Base Classes** define interfaces for each device category
- **Concrete Implementations** provide hardware-specific code
- **InstrumentManager** loads configuration and instantiates devices
- **DeviceExecutor** executes actions on devices
- **ParameterParser** extracts parameters from CSV method files
- **GUI (methods_gui.py)** provides instrument configuration and method building tools

## Supported Device Types

The system currently supports six abstract device types:

1. **LiquidHandler** - Liquid handling robots (e.g., GX281, Ender3)
2. **Pump** - General pumps (e.g., VICI M6, Isametic)
3. **SyringePump** - Syringe pumps with volume selection (e.g., PHD Ultra)
4. **Valves** - Valve controllers (e.g., VICI 6/10/24-way)
5. **TemperatureController** - Temperature control (e.g., TC720)
6. **UV Detectors** - Special devices (DH2000, Ocean Optics) - custom interfaces

---

## Adding New Equipment: Step-by-Step Guide

### Step 1: Choose the Correct Abstract Base Class

Your new device must inherit from one of the existing abstract classes:

| Device Category | Abstract Class | Location | Key Methods |
|----------------|----------------|----------|-------------|
| Liquid Handlers | `LiquidHandler` | `liquid_handlers/liquid_handlers.py` | `connect()`, `home()`, `move_xy()`, `move_z()`, `get_safe_z_height()`, `status()`, `close()` |
| Pumps | `Pump` | `pumps/pumps.py` | `connect()`, `aspirate()`, `dispense()`, `set_flow_rate()`, `stop()`, `status()`, `close()` |
| Syringe Pumps | `SyringePump` | `syringe_pumps/syringe_pumps.py` | Inherits from `Pump` + `select_syringe()` |
| Valves | `Valves` | `valves/valves.py` | `connect()`, `go_to_position()`, `get_position()`, `move_home()`, `stop()`, `status()`, `close()` |
| Temperature Controllers | `TemperatureController` | `temperature_controller/temperature_controller.py` | `connect()`, `set_temperature()`, `get_temperature()`, `stop()`, `status()`, `close()` |

**Important:** All methods marked with `@abc.abstractmethod` **must** be implemented, or Python will raise a `TypeError` when you try to instantiate your class.

### Step 2: Create Your Device Implementation

Create a new Python file in the appropriate subdirectory:

**Example: Adding a New Pump (Tricontinental C24000 Dual Pump)**

```python
# pumps/tricontinental_c24000/tricontinental_c24000.py

from pumps.pumps import Pump
import serial
import time

class TricontinentalC24000(Pump):
    """Driver for Tricontinental C24000 Dual Syringe Pump."""
    
    def __init__(self, port: str, baudrate: int = 9600, name: str = "Tricontinental_C24000"):
        """
        Initialize Tricontinental C24000 dual pump.
        
        Args:
            port: Serial port (e.g., 'COM5' or '/dev/ttyUSB0')
            baudrate: Serial baud rate (default 9600)
            name: Friendly name for logging
        """
        self.port = port
        self.baudrate = baudrate
        self.name = name
        self.serial = None
        self._connected = False
        self._pump_a_position = 0  # Track syringe A position
        self._pump_b_position = 0  # Track syringe B position
    
    def connect(self) -> None:
        """Connect to the pump via serial port."""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=2.0
            )
            time.sleep(0.5)  # Allow hardware to stabilize
            self._connected = True
            print(f"{self.name}: Connected on {self.port}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.name}: {e}")
    
    def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Aspirate specified volume at specified flow rate."""
        if not self._connected:
            raise RuntimeError(f"{self.name}: Not connected")
        
        # Convert µL/min to device-specific units (example)
        device_rate = self._convert_flow_rate(flow_rate_ul_min)
        device_volume = self._convert_volume(volume_ul)
        
        # Send hardware-specific command
        cmd = f"ASP {device_rate} {device_volume}\r\n"
        self.serial.write(cmd.encode())
        
        # Wait for completion or response
        response = self.serial.readline().decode().strip()
        if "ERROR" in response:
            raise RuntimeError(f"{self.name}: Aspirate failed - {response}")
    
    def dispense(self, flow_rate_ul_min: float, volume_ul: float) -> None:
        """Dispense specified volume at specified flow rate."""
        if not self._connected:
            raise RuntimeError(f"{self.name}: Not connected")
        
        device_rate = self._convert_flow_rate(flow_rate_ul_min)
        device_volume = self._convert_volume(volume_ul)
        
        cmd = f"DIS {device_rate} {device_volume}\r\n"
        self.serial.write(cmd.encode())
        
        response = self.serial.readline().decode().strip()
        if "ERROR" in response:
            raise RuntimeError(f"{self.name}: Dispense failed - {response}")
    
    def set_flow_rate(self, flow_rate_ul_min: float) -> None:
        """Set default flow rate for subsequent operations."""
        if not self._connected:
            raise RuntimeError(f"{self.name}: Not connected")
        
        device_rate = self._convert_flow_rate(flow_rate_ul_min)
        cmd = f"SETRATE {device_rate}\r\n"
        self.serial.write(cmd.encode())
    
    def stop(self) -> None:
        """Stop any ongoing pump operation."""
        if not self._connected:
            return
        
        cmd = "STOP\r\n"
        self.serial.write(cmd.encode())
        print(f"{self.name}: Stopped")
    
    def status(self) -> str:
        """Return current pump status."""
        if not self._connected:
            return f"{self.name}: Not connected"
        
        cmd = "STATUS?\r\n"
        self.serial.write(cmd.encode())
        response = self.serial.readline().decode().strip()
        return f"{self.name}: {response}"
    
    def close(self) -> None:
        """Close serial connection."""
        if self.serial and self.serial.is_open:
            self.stop()  # Ensure pump is stopped
            self.serial.close()
            self._connected = False
            print(f"{self.name}: Closed")
    
    # Helper methods (device-specific)
    def _convert_flow_rate(self, ul_min: float) -> int:
        """Convert µL/min to device-specific rate units."""
        # Example: device uses steps/sec, 1 µL/min = 10 steps/sec
        return int(ul_min * 10)
    
    def _convert_volume(self, ul: float) -> int:
        """Convert µL to device-specific volume units."""
        # Example: device uses steps, 1 µL = 100 steps
        return int(ul * 100)
```

### Step 3: Update InstrumentManager

Add your device to `methods/instrument_manager.py`:

**1. Import your class:**

```python
# At the top of instrument_manager.py
from pumps.tricontinental_c24000.tricontinental_c24000 import TricontinentalC24000
```

**2. Add instantiation logic in `initialize_instruments()` method:**

```python
def initialize_instruments(self, config_df):
    """Initializes instrument objects based on configuration DataFrame."""
    # ... existing code ...
    
    for _, row in config_df.iterrows():
        instrument_type = row['InstrumentType'].strip()
        # ... existing parsing ...
        
        # Add your new device type
        elif instrument_type == "Tricontinental_C24000":
            obj = TricontinentalC24000(port=com_port, name=attr_name)
        
        # ... rest of existing code ...
```

### Step 4: Update GUI Configuration (methods_gui.py)

Update `methods/methods_gui.py` to make your device available in the GUI:

**1. Add to INSTRUMENT_CHOICES:**

```python
INSTRUMENT_CHOICES = [
    "GX281",
    "Ender3_Liquid_Handler",
    "VICI_M6_Pump",
    "Isametic",
    "PhdUltraPump",
    "Tricontinental_C24000",  # ← Add your device here
    "Valve6Way",
    # ... rest
]
```

**2. Add to DEFAULT_ROWS (optional - provides example configuration):**

```python
DEFAULT_ROWS = [
    ("GX281", "1", "GX-281", "COM2", ""),
    ("Tricontinental_C24000", "1", "TriconPump", "COM18", ""),  # ← Add example row
    # ... rest
]
```

**3. Add to group_for_instrument_type() function (around line 50):**

```python
def group_for_instrument_type(inst_type: str) -> str:
    """Map instrument type to action group."""
    if inst_type in ("GX281", "Ender3_Liquid_Handler"):
        return "LiquidHandler"
    if inst_type in ("VICI_M6_Pump", "Isametic", "PhdUltraPump", "Tricontinental_C24000"):  # ← Add here
        return "Pump"
    # ... rest
```

**4. Update ACTIONS_BY_GROUP (if needed - for custom actions):**

```python
ACTIONS_BY_GROUP: dict[str, list[str]] = {
    "Pump": ["aspirate", "dispense", "select_syringe"],  # Standard pump actions work
    # ... rest
}
```

**5. Update PARAM_FIELDS (if you have custom actions):**

```python
PARAM_FIELDS: dict[tuple[str, str], list[tuple[str, str]]] = {
    # Standard pump actions use existing parameters
    ("Pump", "aspirate"): [("flow_rate", "Flow rate (µL/min)"), ("volume", "Volume (µL)")],
    ("Pump", "dispense"): [("flow_rate", "Flow rate (µL/min)"), ("volume", "Volume (µL)")],
    # ... rest
}
```

### Step 5: Update DeviceExecutor (if needed)

**Most devices work with existing `execute_pump()`, `execute_valve()`, etc. methods in `device_executors.py`.**

Only add custom execution logic if your device has unique actions not covered by the abstract interface:

```python
# In methods/device_executors.py

def execute_pump(self, action, params, component, pump: Pump):
    """Execute pump actions using abstract interface methods."""
    # Existing code handles standard aspirate/dispense
    
    # Add custom action only if needed
    if action == "initialize_valves":
        if isinstance(pump, TricontinentalC24000):
            pump.initialize_valve_positions()  # Custom method
            self.log_to_csv(component, action, params, "Valve positions initialized")
            return
    
    # ... rest of existing code ...
```

### Step 6: Create __init__.py (optional but recommended)

```python
# pumps/tricontinental_c24000/__init__.py
"""Tricontinental C24000 Dual Pump Driver"""
from .tricontinental_c24000 import TricontinentalC24000

__all__ = ['TricontinentalC24000']
```

### Step 7: Test Your Device

**1. Create a test instrument configuration CSV:**

```csv
InstrumentType,DeviceNumber,Name,COMPort,OtherParams
Tricontinental_C24000,1,TriconPump,COM18,
```

**2. Create a simple method CSV:**

```csv
Component,Action,Parameters,Notes,delay
Tricontinental_C24000_1,aspirate,flow_rate=100;volume=500,Test aspirate,0.5
Tricontinental_C24000_1,dispense,flow_rate=100;volume=500,Test dispense,0.5
```

**3. Test via GUI:**

```bash
auto-zahrt-gui
```

Or programmatically:

```python
from methods import GeneralExperimentMethod

experiment = GeneralExperimentMethod(
    input_file="test_method.csv",
    instrument_config_file="test_instruments.csv"
)
experiment.run_experiment()
```

---

## GUI Utility Scripts

### config_builder.py

Located in `utils/config_builder.py`, this provides a table-based editor for creating instrument configuration CSVs. It's automatically accessible from the main GUI.

**Key Functions:**
- `launch_instrument_csv_builder()` - Opens the builder window
- Uses `INSTRUMENT_CHOICES` and `DEFAULT_ROWS` from `methods_gui.py`

**To extend:** Add your instrument type to `INSTRUMENT_CHOICES` in `methods_gui.py`.

### status_gui.py & status_monitor_gui.py

- **status_gui.py** - Opens CSV status logs for review
- **status_monitor_gui.py** - Real-time instrument monitoring during experiments

**To extend:** Ensure your device implements `status()` method correctly.

---

## Error Handling Best Practices

### 1. Connection Errors

```python
def connect(self) -> None:
    try:
        self.serial = serial.Serial(self.port, self.baudrate, timeout=2.0)
        self._connected = True
    except serial.SerialException as e:
        raise ConnectionError(f"{self.name}: Cannot open {self.port} - {e}")
    except Exception as e:
        raise RuntimeError(f"{self.name}: Unexpected error during connect - {e}")
```

### 2. Operation Errors

```python
def aspirate(self, flow_rate_ul_min: float, volume_ul: float) -> None:
    if not self._connected:
        raise RuntimeError(f"{self.name}: Not connected - call connect() first")
    
    if flow_rate_ul_min <= 0 or volume_ul <= 0:
        raise ValueError(f"{self.name}: flow_rate and volume must be positive")
    
    try:
        # Hardware operation
        self._send_command(f"ASP {flow_rate_ul_min} {volume_ul}")
    except Exception as e:
        # Log but don't crash the entire experiment
        print(f"{self.name}: Aspirate failed - {e}")
        raise
```

### 3. Graceful Shutdown

```python
def close(self) -> None:
    """Ensure safe shutdown even if errors occur."""
    try:
        if self._connected:
            self.stop()  # Stop any ongoing operations
    except Exception as e:
        print(f"{self.name}: Error during stop - {e}")
    
    try:
        if self.serial and self.serial.is_open:
            self.serial.close()
    except Exception as e:
        print(f"{self.name}: Error closing serial - {e}")
    finally:
        self._connected = False
```

---

## CSV Method File Documentation

When adding a new device, document the available actions and parameters for end users:

### Example Documentation Section

**Tricontinental C24000 Pump Actions:**

| Action | Parameters | Description | Example |
|--------|-----------|-------------|---------|
| `aspirate` | `flow_rate=<µL/min>`, `volume=<µL>` | Aspirate liquid | `flow_rate=100, volume=500` |
| `dispense` | `flow_rate=<µL/min>`, `volume=<µL>` | Dispense liquid | `flow_rate=100, volume=500` |
| `set_flow_rate` | `flow_rate=<µL/min>` | Set default flow rate | `flow_rate=200` |

Add this to project README or create a dedicated `DEVICE_REFERENCE.md`.

---

## Testing Requirements

### Minimal Testing Checklist

- [ ] Device connects successfully (`connect()`)
- [ ] All abstract methods implemented
- [ ] Device appears in GUI instrument builder
- [ ] Method CSV accepts device actions
- [ ] Actions execute without errors
- [ ] Device stops cleanly (`stop()`)
- [ ] Device closes cleanly (`close()`)
- [ ] Error messages are informative
- [ ] `status()` returns useful information

### Example Test Script

```python
# test_tricontinental_c24000.py
from pumps.tricontinental_c24000.tricontinental_c24000 import TricontinentalC24000

def test_tricontinental_pump():
    # Initialize
    pump = TricontinentalC24000(port="COM18", name="TestPump")
    
    # Connect
    pump.connect()
    assert pump._connected
    
    # Test operations
    pump.set_flow_rate(100.0)
    pump.aspirate(100.0, 500.0)
    pump.dispense(100.0, 500.0)
    
    # Test status
    status = pump.status()
    assert "TestPump" in status
    
    # Cleanup
    pump.close()
    assert not pump._connected
    
    print("✅ All tests passed!")

if __name__ == "__main__":
    test_tricontinental_pump()
```

---

## Backwards Compatibility Guidelines

### When Modifying Existing Devices

1. **Don't remove or rename public methods** - other code may depend on them
2. **Add optional parameters with defaults** - avoid breaking existing calls
3. **Deprecate gracefully** - warn users before removing features

```python
def old_method(self, param1):
    """DEPRECATED: Use new_method() instead. Will be removed in v4.0."""
    import warnings
    warnings.warn("old_method() is deprecated, use new_method()", DeprecationWarning)
    return self.new_method(param1)
```

4. **Maintain CSV format compatibility** - existing method files should still work
5. **Version your changes** - update `__version__` in `__init__.py`

---

## Adding New Device Types (Advanced)

If you need a device type **outside** the six supported categories (e.g., Spectrometer, Stirrer, Camera):

### This Requires Extensive Changes:

1. **Create new abstract base class** (e.g., `spectrometers/spectrometer.py`)
2. **Update `methods/device_executors.py`** - add `execute_spectrometer()` method
3. **Update `methods/methods.py`** - add device type routing in `run_experiment()`
4. **Update `methods_gui.py`** - add action group to `ACTIONS_BY_GROUP`, `PARAM_FIELDS`
5. **Update `utils/status.py`** - add grouping logic
6. **Update documentation** - README, DEVELOPER_GUIDE, etc.

**Note:** Full documentation for custom device types will be provided in future versions. Contact the development team for assistance.

---

## Quick Reference Checklist

When adding a new device of an existing type:

- [ ] 1. Create implementation file inheriting from abstract class
- [ ] 2. Implement all `@abc.abstractmethod` methods
- [ ] 3. Add import to `instrument_manager.py`
- [ ] 4. Add instantiation logic to `InstrumentManager.initialize_instruments()`
- [ ] 5. Add device type to `INSTRUMENT_CHOICES` in `methods_gui.py`
- [ ] 6. Add device type to `group_for_instrument_type()` in `methods_gui.py`
- [ ] 7. (Optional) Add to `DEFAULT_ROWS` for GUI examples
- [ ] 8. (Optional) Add custom actions to `ACTIONS_BY_GROUP` and `PARAM_FIELDS`
- [ ] 9. (Optional) Add custom execution logic to `device_executors.py`
- [ ] 10. Test with instrument config CSV and method CSV
- [ ] 11. Document actions/parameters for end users

---

## Common Pitfalls

### ❌ Forgot to implement all abstract methods
```python
# This will raise TypeError on instantiation
class MyPump(Pump):
    def connect(self): pass
    # Missing: aspirate, dispense, set_flow_rate, stop, status, close
```

### ❌ Inconsistent units
```python
# Abstract interface expects µL/min, but device uses mL/hr
def aspirate(self, flow_rate_ul_min: float, volume_ul: float):
    # WRONG: passing directly to device
    self._send_command(f"FLOW {flow_rate_ul_min}")
    
    # CORRECT: convert units
    flow_ml_hr = flow_rate_ul_min * 0.06  # µL/min → mL/hr
    self._send_command(f"FLOW {flow_ml_hr}")
```

### ❌ Forgot to update GUI mappings
```python
# Device added to InstrumentManager but not to INSTRUMENT_CHOICES
# Result: GUI won't show the device in dropdowns
```

### ❌ Blocking operations without status updates
```python
# WRONG: blocks for 5 minutes with no feedback
def wait_for_temperature(self):
    time.sleep(300)

# CORRECT: provide periodic status updates
def wait_for_temperature(self):
    for i in range(60):
        current = self.get_temperature()
        print(f"Current temp: {current}°C")
        time.sleep(5)
```

---

## Getting Help

- **Abstract class reference:** See files in respective module folders
- **Example implementations:** Check existing devices (GX281, VICI_M6, TC720)
- **Architecture overview:** See `INSTALLATION_SUMMARY.md`
- **Questions:** Contact Professor Andrew Zahrt

---

## Summary

Adding new equipment to AUTO_ZAHRT follows a consistent pattern:

1. **Inherit from the correct abstract class**
2. **Implement all required methods**
3. **Register in InstrumentManager**
4. **Update GUI configuration**
5. **Test thoroughly**
6. **Document for users**

The abstract base class architecture ensures consistency, maintainability, and backward compatibility across the entire system.
