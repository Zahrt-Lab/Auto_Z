# Auto_Zahrt v3 — Code Review Findings

> Generated 2026-05-31. Full static review across all Python modules.
> Work through these top-to-bottom; critical issues first.

---

## CRITICAL — Fix Before Next Run

- [ ] **Race condition on `_continue_experiment` flag** (`methods/methods.py`, `methods/status_monitor.py`)
  - Written from `StatusMonitor` daemon thread, read in main loop with no lock
  - Fix: Replace bare bool with `threading.Event` (`event.set()` / `event.clear()` / `event.is_set()` are atomic)

- [ ] **Race condition on `_status_monitoring_active`** (`methods/status_monitor.py` ~lines 65, 107, 128)
  - Same issue: written in `stop()` (main thread), read in worker `while` loop
  - Fix: Use `threading.Event` here too

- [ ] **TricontinentalC24000 inverted valve logic** (`devices/.../tricontinental_c24000/tricontinental_c24000.py` ~line 193)
  - `while (not is_output_valve_A) and (not is_output_valve_B):` — pump will never start if one valve is already correct
  - Fix: Change `and` → `or`

- [ ] **UV detector worker thread entirely unprotected** (`devices/.../uv_detectors/uv_detector.py` ~lines 631–667)
  - The `try/except` wrapping the continuous-monitoring worker is completely commented out; any exception silently kills background measurement with no log, no cleanup
  - Fix: Uncomment and restore the exception handler

---

## HIGH — Fix Soon

- [ ] **`DeviceExecutor` no error handling in public methods** (`methods/device_executors.py` ~lines 59–92)
  - All `execute_*` methods delegate with zero try/except; single device failure crashes whole experiment before cleanup
  - Fix: Wrap each call, log error, re-raise typed exception

- [ ] **`PumpExecutor` race on `_pump_threads` / `_active_pumps` lists** (`devices/.../pumps/pump_executor.py` ~lines 150–165)
  - Appended from main thread, iterated in `stop_all_pumps()` with no lock; concurrent calls cause resize-during-iteration crash
  - Fix: Guard both lists with `threading.Lock()`

- [ ] **Failed device connections not removed from instrument registry** (`methods/instrument_manager.py` ~lines 83–91)
  - If `connect()` raises, device stays in `self.instruments`; downstream code uses it as if it's connected
  - Fix: Remove device from registry on failure, or raise to abort experiment setup

- [ ] **UV detector bare `except:` blocks** (`devices/.../uv_detectors/uv_detector.py` ~lines 258, 271, 279, 288, 539)
  - Bare `except:` (no type) catches `SystemExit` / `KeyboardInterrupt` — hides real errors
  - Fix: Replace with `except Exception as e:` and log `e`

- [ ] **UV detector timestamp None-deref** (`devices/.../uv_detectors/uv_detector.py` ~line 646)
  - `time.time() - self._start_time.timestamp()` — raises `AttributeError` if `_start_time` is None
  - Fix: Guard with `if self._start_time is not None:`

---

## MEDIUM — Fix This Cleanup Cycle

- [ ] **Serial port null-deref after init failure** (4 files)
  - `vici_m6_pump.py` ~line 238, `tricontinental_c24000.py` ~line 266, `vici_valves.py` ~line 150: `self.ser.close()` with no null check
  - `mirror_box_365nm.py` ~lines 54, 60: `self.ser.in_waiting` after `close()` can set `self.ser = None`
  - Fix: Add `if self.ser is not None:` guard before each access

- [ ] **`IsmaticPump.safe_shutdown()` is empty** (`devices/.../pumps/isametic_pump/isametic_pump.py` ~line 283)
  - Violates abstract contract; pump never stopped on safe shutdown
  - Fix: Implement stop + port close

- [ ] **Abstract return type violations**
  - `IsmaticPump.status()` returns `float` but abstract says `str`
  - `ViciValve.get_position()` returns raw `str` but abstract says `int`
  - Fix: Align implementations to abstract signatures (or update abstract with proper type)

- [ ] **Control file I/O race** (`methods/experiment_logger.py` ~line 116, `methods/methods.py` ~line 268)
  - `StatusMonitor` reads `instrument_control.txt` while `convergence_stop()` writes it; no file lock
  - Fix: Shared `threading.Lock`, or replace file-based signaling with `threading.Event`

- [ ] **`_close_all_instruments()` unreachable on exception** (`methods/methods.py` ~lines 209–229)
  - `safe_shutdown()` per device can raise; if it does, `_close_all_instruments()` never runs → serial ports leak
  - Fix: Wrap the per-device shutdown loop in try/finally

- [ ] **Debug print left in production** (`methods/status_monitor.py` ~lines 73–74)
  - `#TODO: Remove this print` + live `print(f"continue_flag in status monitor:...")` still present
  - Fix: Remove both lines

- [ ] **Zombie thread risk in `StatusMonitor.stop()`** (`methods/status_monitor.py` ~lines 129–131)
  - Joins with 5-second timeout, sets `_status_monitor_thread = None` even if still alive; thread keeps writing to CSV
  - Fix: Log warning if `is_alive()` after join; send a harder stop signal

- [ ] **`registry_loader.py` unguarded dynamic import** (`methods/registry_loader.py` ~lines 114–115)
  - `importlib.import_module()` and `getattr()` with no try/except; bad TOML crashes entire startup
  - Fix: Wrap with try/except, raise descriptive error

- [ ] **`serial_DT_transporter.py` exception type mismatch** (`utils/serial_DT_transporter.py` ~lines 62–66)
  - `read_until()` raises `serial.SerialTimeoutException` but re-raised as generic `TimeoutError`; callers catching serial exceptions miss it
  - Fix: Re-raise original type or document the deliberate translation

- [ ] **CSV log opened/closed on every write** (`methods/experiment_logger.py` ~line 85, `methods/status_monitor.py` ~lines 98–103)
  - One row written per open/close cycle; high I/O and data loss risk on crash
  - Fix: Keep file handle open, call `flush()` after each write

---

## LOW — Clean Up When Convenient

- [ ] **Hardcoded control file path strings in GUI** (`user_interface/methods_gui.py` ~lines 58–59)
  - `"instrument_control.txt"` / `"dh2000_light_source_control.txt"` literals
  - Fix: Reference shared constants from `experiment_logger.py`

- [ ] **Wrong debug print in VICI M6 pump** (`devices/.../pumps/vici_m6_pump/vici_m6_pump.py` ~line 193)
  - `time.time() - pump_time` where `pump_time` is a calculated duration, not a start timestamp → wrong arithmetic AND it's a debug print
  - Fix: Remove

- [ ] **Unused `start_time` parameter in `DeviceExecutor.__init__`** (`methods/device_executors.py` ~line 42)
  - Accepted but never used or passed to sub-executors
  - Fix: Remove parameter

- [ ] **Unused `traceback` import** (`devices/.../uv_detectors/uv_detector.py` ~line 20)
  - Only needed inside the commented-out exception handler
  - Fix: Remove (restore when handler is restored)

- [ ] **`parameter_parser.py` silent float coercion failure** (`methods/parameter_parser.py` ~lines 43–47)
  - `float()` failure silently stores value as string; `"temperature=37.5V"` becomes `str` and device receives wrong type at runtime
  - Fix: Log a warning when numeric conversion falls back to string

---

## Verification After Fixes

```bash
# Run all simulation tests (no hardware needed)
pytest test/simulation/ -v

# Confirm threading fixes with a simulated emergency stop mid-run
# Confirm _close_all_instruments() fires even when safe_shutdown() raises
```