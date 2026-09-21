# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Andrew Zahrt
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
Registry loader for General Methods.

Reads device_registry.toml once at import time and provides accessor
functions used by InstrumentManager, the GUI, and utils/status.py.

To add a new device: edit device_registry.toml only; no Python changes needed
for devices that fit an existing abstract base class.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any
import tomli as tomllib

# Contains the file path to the device registry TOML file
_REGISTRY_PATH: Path = Path(__file__).parent / "device_registry.toml"
# Cached registry data loaded from the TOML file, stored as a global variable
_registry: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    global _registry
    if _registry is None:
        with open(_REGISTRY_PATH, "rb") as f:
            _registry = tomllib.load(f)
    return _registry


# ── Device type queries ────────────────────────────────────────────────────────


def get_all_types() -> list[str]:
    """Return all registered instrument type strings (for GUI dropdowns)."""
    return list(_load()["devices"].keys())

# For a given instrument type
# TODO: When is the get_group function needed?
def get_group(instrument_type: str) -> str | None:
    """Return the executor/GUI group for a given instrument type, or None."""
    return _load()["devices"].get(instrument_type, {}).get("group")


# ── GUI metadata ───────────────────────────────────────────────────────────────


def get_actions(group: str) -> list[str]:
    """Return the ordered action list for a group (used by GUI action dropdown)."""
    return _load()["groups"].get(group, {}).get("actions", [])


def get_param_fields(group: str, action: str) -> list[tuple[str, str]]:
    """
    Return ordered (key, label) pairs for a group+action combination.
    Returns an empty list if the action takes no parameters.
    """
    params = _load()["groups"].get(group, {}).get("params", {}).get(action, {})
    return list(params.items())


# ── Default rows ───────────────────────────────────────────────────────────────


def get_default_rows() -> list[tuple[str, ...]]:
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

def build_instance(
    instrument_type: str, csv_row: Any, context: dict[str, Any] | None = None
) -> object:
    """
    Instantiate a device from the registry.

    Parameters:
     - instrument_type: The InstrumentType string from the instrument config CSV.
     - csv_row: A pandas Series (or dict-like) for the instrument CSV row.
     - context: Runtime values injected by InstrumentManager.

    Returns:
     - The device object.

    Raises:
        ValueError: If instrument_type is not in the registry.
    """
    context = context or {}
    registry = _load()
    entry = registry["devices"].get(instrument_type)
    if entry is None:
        raise ValueError(
            f"Unknown instrument type: {instrument_type!r}. "
            "Add it to methods/device_registry.toml."
        )

    # Dynamic import
    module = importlib.import_module(entry["import_path"])
    cls = getattr(module, entry["class_name"])

    # Compute the instrument's attribute name (same logic as the old elif chain)
    device_number = str(csv_row.get("DeviceNumber", "")).strip()
    attr_name = (
        f"{instrument_type}_{device_number}" if device_number else instrument_type
    )

    kwargs: dict[str, Any] = {}

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
