# Big TODO List in order

1) Write test cases of all equipment used in project_dead_mans_fingers to ensure there is no logic issues and equipment hardware is working to help with troubleshooting.

2) Currently there are lot of serial connections that are the same logic, with connect, drain, etc, next priority is to move these utils in their own scripts and functions to make it cleaner.

3) Currently with the status button, this causes a lot errors if two commands run at the same time, threading is being used currently but async should be used in the future to prevent any of this conflict.

4) The methods directory is a bit messy right now to get everything to work, need to clean this up and make it easier to add new instruments for future users. 

5) A lot of the pump logic is the same, can maybe include some general purpose math for all our test ases to ensure everything is working. 

6) Directories are getting crowded should be cleaned up and organized to make it cleaner for people. 

---

## Publication Polish (Supplementary Material for Chemistry Paper)

Surface-level polish only — no architectural changes. Priority order:

### 1. Type Hints
Add type annotations to all public method signatures in:
- `methods/methods.py` — `__init__`, `run_experiment()`, `shutdown()`, `emergency_stop()`
- `methods/parameter_parser.py` — all static methods (return types entirely missing)
- `methods/experiment_logger.py` — `log_to_csv()`, `create_output_directory()`
- `methods/instrument_manager.py` — `initialize_instruments()`, `load_config()`
- `methods/device_executors.py` — all `execute_*` signatures
- `methods/status_monitor.py` — `__init__`, `start()`, `stop()`
- Abstract base classes: `pumps/pumps.py`, `valves/valves.py`, `uv_detectors/uv_detector.py`, `temperature_controller/temperature_controller.py`, `liquid_handlers/liquid_handlers.py`
- Validate with: `mypy methods/ --ignore-missing-imports`

### 2. Docstrings — Standardize to Google Style
Use this format everywhere:
```
def method(self, param: str) -> bool:
    """One-line summary.

    Args:
        param: Description.

    Returns:
        Description.

    Raises:
        ValueError: When param is malformed.
    """
```
Files with missing/incomplete docstrings:
- `methods/methods.py` — `_set_continue_flag()`, `_check_continue_flag()`, `wait_for_pumps()`, `shutdown()`
- `methods/device_executors.py` — `_wait_temperature_convergence()` (complex, no docstring)
- `methods/status_monitor.py` — `_status_monitor_worker()` (background thread, undocumented)
- `methods/parameter_parser.py` — all static methods need Args/Returns sections

Remove large commented-out code blocks (use git history instead):
- `uv_detectors/uv_detector.py` lines ~27, 43–44
- `pumps/tricontinental_c24000/tricontinental_c24000.py` lines ~27–46

### 3. Error Handling (Surface Fixes)
- **Fragile CSV parsing** (`parameter_parser.py`): wrap dict comprehensions in try-except; handle empty params string
- **Silent config failure** (`instrument_manager.py`): raise `RuntimeError` instead of silently continuing with empty dict when config load fails
- **Silent name assignment** (`instrument_manager.py`): replace bare `except: pass` with a warning print
- **Path separator** (`methods.py` line 52, `experiment_logger.py` line 24): replace `"Experimental_Data//Outputs"` with `os.path.join()` or `pathlib.Path`

### 4. Tests — Fill Critical Gaps
New files to create in `test/unit/` and `test/integration/`:
- `test/unit/test_parameter_parser.py` — valid inputs, empty string, missing keys, malformed params
- `test/unit/test_experiment_logger.py` — directory creation, CSV writes, append behavior (use `tmp_path`)
- `test/integration/test_instrument_manager.py` — valid CSV load, missing file error, empty config

Target: ≥70% line coverage for `parameter_parser.py` and `experiment_logger.py`

### 5. pyproject.toml Metadata
- Add `author_email` and `project.urls` (repository URL)
- Add license classifier
- Fix `exclude = ["test*"]` — currently excludes test dirs from the package unintentionally

### Verification Commands
```bash
pytest test/unit/ test/integration/ -v --cov=methods --cov-report=term-missing
mypy methods/ --ignore-missing-imports
```