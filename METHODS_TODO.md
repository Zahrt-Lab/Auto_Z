# Methods Package — Code Cleanup TODO

Generated from code review session (2026-04-03).

---

## Quick Wins (Low Risk)

- [ ] **Generalize `ParameterParser`** (`methods/parameter_parser.py`)
  - 6 near-identical methods all do `.split('=')` in a dict comprehension
  - Replace with a single `extract_param(key, type, params)` helper
  - Will cut the file to roughly a third of its current size

- [ ] **Add validation to parameter parsing** (`methods/parameter_parser.py`)
  - `.split('=')` raises `ValueError` on any malformed CSV row with no useful error message
  - Wrap parsing in try/except and raise a descriptive error (include row content)

- [ ] **Replace `print()` with `logging`** (all files in `methods/`)
  - 30+ bare print statements with no levels or filtering
  - Switch to Python's `logging` module so output can be leveled, redirected, or suppressed

---

## Medium Effort

- [ ] **Replace `_continue_experiment` boolean with `threading.Event`** (`methods/methods.py`, `methods/status_monitor.py`)
  - Boolean flag is set from `StatusMonitor` background thread and read on main thread without a lock
  - Replace with `threading.Event()` for proper cross-thread signaling

- [ ] **Replace `isinstance()` routing chain with a dispatch table** (`methods/methods.py` ~line 177)
  - Current chain requires editing `methods.py` every time a new device type is added
  - Use the device group string from `device_registry.toml` as a dispatch key instead

- [ ] **Consolidate connect/disconnect logic** (`methods/instrument_manager.py`, `methods/methods.py`)
  - Same connect/disconnect pattern duplicated in 3 places: `InstrumentManager`, `close_all_connections()`, `emergency_stop()`
  - Extract into a shared helper

---

## Larger Refactors (When Time Allows)

- [ ] **Standardize liquid handler abstract interface** (`liquid_handlers/liquid_handlers.py`, `methods/device_executors.py`)
  - `device_executors.py` uses `hasattr()` checks at lines 57, 89, 102 to distinguish GX281 from Ender3
  - The abstract base class should define a common contract (e.g., `move_xy(bed, well)`) so runtime probing is unnecessary

- [ ] **Simplify `shutdown()` method** (`methods/methods.py` ~line 239)
  - Currently 74 lines with nested logic and an inverted control file meaning for DH2000
  - Extract DH2000 shutdown and temperature controller shutdown into their own private methods
  - Clarify or flip the inverted boolean semantics (the comment currently notes the inversion)

- [ ] **Resolve the 6 open TODOs** (`methods/methods.py` lines 10–16)
  - Tricontinental pump not yet integrated
  - UV detector calibration not automated
  - Light source tunable parameters not implemented
  - Light source state persistence at end of method not working

---

## Notes
- The `device_registry.toml` + `RegistryLoader` pattern is good — keep building on it
- Abstract device base classes (`Pump`, `Valves`, etc.) are the right approach — enforce them more strictly
- Pump async threading with `wait_for_pumps` works correctly — no changes needed there