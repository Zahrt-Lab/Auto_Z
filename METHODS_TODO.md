# Methods Package — Code Cleanup TODO

Re-evaluated after code changes (2026-04-05). Original review: 2026-04-03.

---

## Quick Wins (Low Risk)

- [ ] **Fix inline `split('=')` in `TemperatureExecutor` and `PhotoReactorExecutor`**
  - `devices/industry_components/temperature_controller/temperature_executor.py`
  - `devices/custom_components/light_source/photo_reactor_executor.py`
  - Both still use raw `{k: v for k, v in (p.split('=') for p in ...)}` dict comprehensions
  - Replace with `parse_params()` from `methods/parameter_parser.py` — ~3-line change per file
  - *Introduced by the executor split refactor (commit `991828d`)*

- [ ] **Fix `pump_executor.py` None-type crash on missing parameters**
  - `devices/industry_components/pumps/pump_executor.py`
  - `parse_params().get('flow_rate')` returns `None` when the key is absent; `if flow_rate <= 0` then raises `TypeError: '<=' not supported between instances of 'NoneType' and 'int'`
  - Add default values: `flow_rate = params.get('flow_rate', 0)` and `volume = params.get('volume', 0)`, or add an explicit missing-key error before comparison
  - *Regression introduced by removing the old `ParameterParser.extract_flow_rate_and_volume()` which had defaults*

- [ ] **Replace `print()` with `log_to_csv()`** (all executor and methods files)
  - Goal: route all output through `self.log_to_csv()` consistently; remove remaining bare `print()` calls
  - Remaining print locations:
    - `methods/instrument_manager.py` — 8 prints (untouched by recent commits)
    - `methods/experiment_logger.py` — 3 prints
    - `methods/status_monitor.py` — 4 prints
    - `methods/methods.py` — 2 prints (`INITIALIZING EMERGENCY STOP`, `EMERGENCY STOP COMPLETED`)
    - `devices/industry_components/temperature_controller/temperature_executor.py` — 8 prints (new file, all bare prints)
    - `devices/industry_components/liquid_handlers/liquid_handler_executor.py` — 1 print
  - *Note: `parse_params()` already handles malformed input gracefully; the old "Add validation" TODO is now resolved by this*

---

## Medium Effort

- [ ] **Replace `_continue_experiment` boolean with `threading.Event`** (`methods/methods.py`, `methods/status_monitor.py`)
  - Boolean flag is set from `StatusMonitor` background thread and read on main thread without a lock
  - Replace with `threading.Event()` for proper cross-thread signaling
  - The existing callback interface (`continue_flag_callback`) makes this migration relatively clean — callers already use a callable, so swapping the bool for an Event won't require changing their signatures

- [ ] **Replace `isinstance()` routing chain with a dispatch table** (`methods/methods.py` ~line 177)
  - Current chain requires editing `methods.py` every time a new device type is added
  - Use the device group string from `device_registry.toml` as a dispatch key; each group now has its own sub-executor in `methods/device_executors.py`, so a `{group: sub_executor.execute}` dict would replace the chain entirely

- [ ] **Consolidate connect/disconnect logic** (`methods/instrument_manager.py`, `methods/methods.py`)
  - Same connect/disconnect pattern duplicated in 3 places: `InstrumentManager`, `close_all_connections()`, `emergency_stop()`
  - Extract into a shared helper

---

## Larger Refactors (When Time Allows)

- [ ] **Standardize liquid handler abstract interface**
  - `devices/industry_components/liquid_handlers/liquid_handler_executor.py` — `hasattr()` checks at ~lines 30, 55, 68 distinguish GX281 from Ender3 at runtime
  - `liquid_handlers/liquid_handlers.py` — abstract base class
  - Define a common contract (e.g., `move_xy(bed, well)`) in the abstract base so runtime probing is unnecessary

- [ ] **Simplify `shutdown()` method** (`methods/methods.py` ~line 239)
  - Currently ~74 lines with nested logic and an inverted control file meaning for DH2000
  - Extract DH2000 shutdown and temperature controller shutdown into their own private methods
  - Clarify or flip the inverted boolean semantics (`skip_dh2000 = True` means "do NOT touch DH2000")

- [ ] **Resolve open inline TODOs** (`methods/methods.py` lines 10–16, `devices/custom_components/light_source/photo_reactor_executor.py` line 17)
  - Tricontinental pump not yet integrated
  - UV detector calibration not automated
  - Light source tunable parameters not implemented
  - Light source state persistence at end of method not working
  - PhotoReactor should be generic — currently only `MirrorBox365nm` is implemented; abstract interface needs to support other reactor types

---

## Completed

- [x] **Generalize `ParameterParser`** — replaced 6 near-identical `.split('=')` methods with a single `parse_params(key_value_string)` helper in `methods/parameter_parser.py` *(commit `8e80ecf`)*
- [x] **Rename `LightSourceBase` → `PhotoReactor`** — abstract class renamed across `light_source_base.py`, `mirror_box_365nm.py`, `device_executors.py`, `methods.py`, and tests *(commit `b265260`)*
- [x] **Split monolithic `DeviceExecutor` into per-device sub-executors** — 7 sub-executors now live next to their abstract base classes in `devices/`; `methods/device_executors.py` is a thin coordinator *(commit `991828d`)*

---

## Notes
- The `device_registry.toml` + `RegistryLoader` pattern is good — keep building on it
- Abstract device base classes (`Pump`, `Valves`, etc.) are the right approach — enforce them more strictly
- Pump async threading with `wait_for_pumps` works correctly — no changes needed there
- `parse_params()` uses `split('=', 1)` and skips malformed entries — use it consistently across all executors
