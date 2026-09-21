# Tecan Pump Module

## Overview

The Tecan pump module provides control for dual-syringe Tecan pumps (models with A/B pump addressing) used in the Auto_Z laboratory automation system. It implements a three-layer architecture:

1. **High-level abstraction** (`tecan_pump.py`) — implements the `Pump` interface
2. **Mid-level driver** (`tecan_pump_driver.py`) — Tecan protocol and hardware control
3. **Low-level transport** (`serial_DT_transporter.py` in `utils/`) — raw serial communication

---

## Architecture

### Layer 1: `Tecan_pump` Class (tecan_pump.py)

The top-level API that conforms to the Auto_Z `Pump` abstract interface. This is what the rest of the system interacts with.

**Key Methods:**
- `connect()` — Establishes serial connection and initializes both pump A and B
- `aspirate()` — Not implemented (Tecan pump uses continuous flow instead)
- `dispense()` — Runs continuous flow for a calculated duration based on volume and flow rate
- `set_flow_rate()` — Stores the desired flow rate for later use
- `stop()` — Stops both pump A and B immediately
- `status()` — Returns pump status (not fully implemented)
- `close()` / `safe_shutdown()` — Clean disconnection

**Implementation Notes:**
- Dual-pump architecture: Each Tecan pump has two internal pumps (A and B) for continuous aspiration/dispensing cycles
- Flow control: Uses calculated pump speed (pulses/second) derived from desired flow rate (µL/min)
- Volume control: Duration is calculated to deliver the requested volume at the specified flow rate

### Layer 2: `Tecan_driver` Class (tecan_pump_driver.py)

Mid-level driver that encapsulates Tecan protocol details and pump-specific command building.

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `connect()` | Opens serial connection via `SerialDTTransport` |
| `disconnect()` | Closes serial connection |
| `initialize_pump(pump, resolution)` | Sends init command to pump A or B |
| `is_initialized(pump)` | Queries pump and checks if initialized (reads error code from response) |
| `check_until_initialized(pump, timeout)` | Polls `is_initialized()` until success or timeout |
| `start_pump(speed, pump)` | Starts pump at given speed (pulses/second) |
| `stop_pump(pump)` | Stops pump immediately |
| `run_continuous_flow(...)` | Composes and sends continuous flow commands for both pumps |
| `compose_command_continuous_flow_A()` | Builds Tecan protocol command string for pump A |
| `compose_command_continuous_flow_B()` | Builds Tecan protocol command string for pump B |

**Tecan Protocol:**
- Commands use DT protocol format: `/{address}[command_chars]`
- Addresses: `1` = pump A, `2` = pump B
- Response format: `/0{status}{data}\x03\r\n`
- Status byte encodes pump state; error code extracted via bitwise AND (`& 0x0F`)
- Error code `7` = "Pump not initialized"

### Layer 3: `SerialDTTransport` Class (utils/serial_DT_transporter.py)

Low-level serial transport for all DT/Tecan protocol communication. Handles:

**Key Methods:**
- `connect()` — Opens serial port with specified parameters
- `disconnect()` — Closes serial port
- `send_command(command)` — Sends raw command string (encodes to bytes, writes to serial)
- `read_response()` — Reads until ETX (`\x03`), consumes CR/LF, returns decoded ASCII string
- `query(command)` — Sends command, waits 0.5s, reads response (blocking request/response)
- `parse_dt_response(response)` — Parses response format, returns dict with `status` and `data`

**Serial Configuration:**
- Default: COM16, 9600 baud, 1-second timeout
- All communication is ASCII-encoded
- Responses terminated with ETX (`\x03`), CR (`\r`), LF (`\n`)

---

## Data Flow Example: Dispense Operation

```
┌──────────────────────────────────────────────────────────────┐
│ User calls: pump.dispense(flow_rate_ul_min=100, volume_ul=500)
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌────────────────────────────────────────┐
        │ Tecan_pump.dispense()                  │
        ├────────────────────────────────────────┤
        │ 1. Calculate time_sec from volume      │
        │    time_sec = (500 µL / 100 µL/min)   │
        │             = 5 min × 60 = 300 sec    │
        │                                        │
        │ 2. Calculate pump speed (pulses/sec)  │
        │    pulse_per_µL = 6.67 pulses/µL      │
        │    pulses/min = 100 × 6.67 = 667      │
        │    speed = 667 / 60 ≈ 11.1 pulses/s  │
        │                                        │
        │ 3. Call driver.run_continuous_flow()  │
        └────────────────────────────────────────┘
                            │
                            ▼
        ┌────────────────────────────────────────┐
        │ Tecan_driver.run_continuous_flow()     │
        ├────────────────────────────────────────┤
        │ 1. Compose command for pump A:        │
        │    "N2J7V26000IA24000OV11.1j1000...GR"│
        │                                        │
        │ 2. Compose command for pump B:        │
        │    "N2J7V26000IA24000gJ7H0OV11.1...GR"│
        │                                        │
        │ 3. Send both to serial transport      │
        └────────────────────────────────────────┘
                            │
                            ▼
        ┌────────────────────────────────────────┐
        │ SerialDTTransport.send_command()       │
        ├────────────────────────────────────────┤
        │ 1. Encode command string to bytes     │
        │ 2. Write to serial.write()            │
        │ 3. Return (no response expected)      │
        └────────────────────────────────────────┘
                            │
                            ▼
        ┌────────────────────────────────────────┐
        │ Tecan_pump.dispense() (continued)     │
        ├────────────────────────────────────────┤
        │ 1. time.sleep(300 seconds)            │
        │    [Pump runs, dispensing liquid]     │
        │                                        │
        │ 2. Call driver.stop() when done       │
        │    [Stops pump A and B]               │
        └────────────────────────────────────────┘
```

---

## Design Patterns

### 1. **Three-Layer Separation of Concerns**
- **Layer 1 (Pump):** Orchestrates operations, implements interface, manages timing
- **Layer 2 (Driver):** Tecan protocol expertise, command composition, pump addressing
- **Layer 3 (Transport):** Serial port I/O, encoding/decoding, basic DT protocol parsing

**Benefit:** Changes to Tecan firmware protocol only require updates to Layer 2, not the rest of the system.

### 2. **Dual-Pump Symmetry**
The Tecan pump contains two internal pumps (A and B) that work in tandem:
- Pump A aspirates while Pump B dispenses
- Commands are composed separately for each (`compose_command_continuous_flow_A` vs `_B`)
- Both pumps are initialized, monitored, and stopped together

### 3. **Asynchronous-Friendly Design**
Dispense operations are intentionally **blocking** (call `time.sleep()`):
- The orchestrator (`GeneralExperimentMethod`) can spawn dispense calls as threads
- Each thread independently waits for its dispensing to complete
- Multiple pumps can dispense in parallel

---

## Key Implementation Details

### Flow Rate Conversion
Tecan pumps operate in **pulses/second**. The conversion chain:

$$\text{flow rate (µL/min)} \xrightarrow{\div 60} \text{pulses/sec} \xrightarrow{\times 0.15} \text{µL/sec}$$

**Calibration note:** The constant `0.15 µL/pulse` is based on:
- 1 mL syringe (1000 µL)
- 24,000 pump steps = 1000 µL → 0.04167 µL/step
- Resolution = 2 → 3.6 steps/pulse → 0.15 µL/pulse

### Initialization Sequence
```
1. Tecan_pump.connect()
   → Tecan_driver.connect()
      → SerialDTTransport.connect() [opens COM port]
   
2. For pump A and B:
   → Tecan_driver.initialize_pump(pump, resolution=0)
      → Sends: "/{addr}N{resolution}ZR"
   
   → Tecan_driver.check_until_initialized(pump, timeout=60)
      → Polls is_initialized() every 5 seconds
      → Queries: "/{addr}Q"
      → Parses response, checks error code
      → Returns when error_code != 7
```

### Command Structure Example
```
Pump A continuous flow initialization:
  N2          → Set resolution to 2
  J7          → Set auxiliary inputs to HIGH
  V26000      → Set initial speed
  IA24000     → Set input position of valve and move plunger to step 24000
  OVA0        → Set output position of valve and move plunger to step 0
  j1000       → Step which the other pump is activated in continuous flow mode
  g           → Start the loop
  GR          → Run loopcommand
```

---

## Limitations & TODOs

| Issue | Status | Note |
|-------|--------|------|
| `aspirate()` | Not implemented | Tecan pump doesn't support standalone aspiration; only continuous flow |
| `status()` | Placeholder | Returns hardcoded string; full implementation pending |
| `is_running()` | Not implemented | Need method to check if pump is actively running |
| Error handling | Basic | Prints errors but doesn't raise exceptions consistently |
| Response validation | Minimal | Only checks error code, not data content |

---

## Usage Example

```python
from devices.industry_components.pumps.tecan_pumps.tecan_pump import Tecan_pump

# Initialize
pump = Tecan_pump(port='COM16', baud_rate=9600, timeout=1)

# Connect and auto-initialize both internal pumps
pump.connect()

# Set flow rate
pump.set_flow_rate(100)  # µL/min

# Dispense 500 µL (will run for 5 minutes at 100 µL/min)
pump.dispense(flow_rate_ul_min=100, volume_ul=500)

# Stop and disconnect
pump.stop()
pump.close()
```

---

## Related Files
- [Pump Abstract Base](../pumps.py) — Interface definition
- [Serial DT Transport](../../../../utils/serial_DT_transporter.py) — Low-level serial
- [Experiment Orchestrator](../../../../methods/methods.py) — Calls pump methods
- [Device Executors](../../../../methods/device_executors.py) — Routes CSV actions to pump
