# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Registry loader for AUTO_ZAHRT.

Reads device_registry.toml once at import time and provides accessor
functions used by InstrumentManager, the GUI, and utils/status.py.

To add a new device: edit device_registry.toml only — no Python changes needed
for devices that fit an existing abstract base class.
"""

import importlib
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

_REGISTRY_PATH = Path(__file__).parent / "device_registry.toml"
_registry: Optional[dict] = None


def _load() -> dict:
    global _registry
    if _registry is None:
        with open(_REGISTRY_PATH, "rb") as f:
            _registry = tomllib.load(f)
    return _registry


# ── Device type queries ────────────────────────────────────────────────────────

def get_all_types() -> List[str]:
    """Return all registered instrument type strings (for GUI dropdowns)."""
    return list(_load()["devices"].keys())


def get_group(instrument_type: str) -> Optional[str]:
    """Return the executor/GUI group for a given instrument type, or None."""
    return _load()["devices"].get(instrument_type, {}).get("group")


# ── GUI metadata ───────────────────────────────────────────────────────────────

def get_actions(group: str) -> List[str]:
    """Return the ordered action list for a group (used by GUI action dropdown)."""
    return _load()["groups"].get(group, {}).get("actions", [])


def get_param_fields(group: str, action: str) -> List[Tuple[str, str]]:
    """
    Return ordered (key, label) pairs for a group+action combination.
    Returns an empty list if the action takes no parameters.
    """
    params = _load()["groups"].get(group, {}).get("params", {}).get(action, {})
    return list(params.items())


# ── Default rows ───────────────────────────────────────────────────────────────

def get_default_rows() -> List[Tuple[str, ...]]:
    """
    Return default instrument CSV rows for the GUI's InstrumentCSVBuilder.
    Each row is a tuple of (InstrumentType, DeviceNumber, Name, COMPort, OtherParams).
    """
    defaults = _load().get("defaults", [])
    return [
        (
            d["InstrumentType"],
            d["DeviceNumber"],
            d["Name"],
            d["COMPort"],
            d["OtherParams"],
        )
        for d in defaults
    ]


# ── Device instantiation ───────────────────────────────────────────────────────

def build_instance(instrument_type: str, csv_row, context: Optional[dict] = None) -> object:
    """
    Instantiate a device from the registry.

    Args:
        instrument_type: The InstrumentType string from the instrument config CSV.
        csv_row:         A pandas Series (or dict-like) for the instrument CSV row.
        context:         Runtime values injected by InstrumentManager, e.g.
                         {"experiment_subdir": "/path/to/run/dir"}.

    Returns:
        The constructed device object.

    Raises:
        ValueError: If instrument_type is not in the registry.
    """
    context = context or {}
    registry = _load()
    entry = registry["devices"].get(instrument_type)
    if entry is None:
        raise ValueError(f"Unknown instrument type: {instrument_type!r}. "
                         "Add it to methods/device_registry.toml.")

    # Dynamic import
    module = importlib.import_module(entry["import_path"])
    cls = getattr(module, entry["class_name"])

    # Compute the instrument's attribute name (same logic as the old elif chain)
    device_number = str(csv_row.get("DeviceNumber", "")).strip()
    attr_name = f"{instrument_type}_{device_number}" if device_number else instrument_type

    kwargs: dict = {}

    # COM port
    if "port_kwarg" in entry:
        com_port = csv_row.get("COMPort")
        if isinstance(com_port, str):
            com_port = com_port.strip() or None
        kwargs[entry["port_kwarg"]] = com_port

    # Instrument name (passed in constructor)
    if "name_kwarg" in entry:
        kwargs[entry["name_kwarg"]] = attr_name

    # Hard-coded constructor values
    for k, v in entry.get("fixed_kwargs", {}).items():
        kwargs[k] = v

    # Runtime-injected values (e.g. experiment_subdir → output_dir)
    for kwarg_name, context_key in entry.get("context_kwargs", {}).items():
        kwargs[kwarg_name] = context.get(context_key)

    obj = cls(**kwargs)

    # For devices that don't accept 'name' in their constructor, set it after
    if "name_kwarg" not in entry:
        try:
            obj.name = attr_name
        except Exception:
            pass

    return obj
