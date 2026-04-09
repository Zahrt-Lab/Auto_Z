# USB VID/PID-Based Instrument Port Identification

## Problem

COM port labels (`COM5`, `COM17`, `/dev/ttyUSB0`) are assigned by the OS at
connection time and can change whenever a device is reconnected, a USB hub is
swapped, or the system reboots. This forces manual reconfiguration of the
instrument config CSV after every port reassignment.

**Goal:** Replace COM port labels with stable hardware identifiers so instruments
are found automatically regardless of which port label the OS assigns.

---

## Key Challenge: Duplicate VID:PID

USB devices expose a **VID** (vendor ID) and **PID** (product ID). These
identify the device *model*, not the individual unit. Two VICI M6 pumps — or
any two instruments using the same USB-to-serial adapter chip (e.g., FTDI
FT232) — will share the same VID:PID.

With VID+PID alone you cannot tell them apart. You need a third identifier.

---

## Recommended Approach: USB Physical Port Location

`serial.tools.list_ports` (part of pyserial) exposes a `location` attribute for
each port. This is the USB hub path — the physical route through the USB
topology to reach the device (e.g., `1-1.2` on Linux, `1-1-2` on Windows).

**Key properties:**
- Works on both Windows and Linux with no extra tools
- Stable across reboots and reconnects *as long as the device stays plugged
  into the same physical USB port*
- No hardware modification required
- Distinguishes two devices with identical VID:PID that are on different ports

**One trade-off:** if you move a device to a different USB port, you need to
update the `USBLocation` entry in the config CSV. This is a one-time action per
physical relocation, which is far less frequent than OS-driven port reassignment.

---

## Alternative: FTDI Serial Number Programming

If your devices use FTDI USB-to-serial chips (very common), you can burn a
unique serial number into each adapter once. After that, `p.serial_number`
reliably distinguishes identical devices regardless of which port they are
plugged into.

**Tools:**
- Windows: [FT_PROG](https://ftdichip.com/utilities/#ft_prog) (FTDI official, free GUI)
- Linux: `ftdi_eeprom` or [`ftx-prog`](https://github.com/richardeoin/ftx-prog)

This is the most robust long-term solution if you are willing to do the one-time
per-device setup.

---

## Step 1: Discover Your Devices' VID, PID, and Location

Run this snippet on the lab computer with all instruments connected:

```python
import serial.tools.list_ports

for p in serial.tools.list_ports.comports():
    vid = f"{p.vid:04X}" if p.vid else "N/A"
    pid = f"{p.pid:04X}" if p.pid else "N/A"
    print(f"Port:     {p.device}")
    print(f"  Desc:   {p.description}")
    print(f"  VID:    {vid}")
    print(f"  PID:    {pid}")
    print(f"  Serial: {p.serial_number}")
    print(f"  Loc:    {p.location}")
    print()
```

Or from the terminal (pyserial built-in):

```bash
python -m serial.tools.list_ports -v
```

Record the `VID`, `PID`, and `Loc` values for each instrument. Plug in one
device at a time if you need to be sure which entry corresponds to which
instrument.

---

## Step 2: Update the Instrument Config CSV

Replace the `COMPort` column with three new columns: `VID`, `PID`, `USBLocation`.

**Before:**
```csv
InstrumentType, DeviceNumber, Name,  COMPort
VICI_M6_Pump,   1,            Pump1, COM17
VICI_M6_Pump,   2,            Pump2, COM18
Temperature,    1,            TC720, COM12
MirrorBox,      1,            UV365, COM9
DH2000,         1,            DH2000, COM10
```

**After:**
```csv
InstrumentType, DeviceNumber, Name,  VID,  PID,  USBLocation
VICI_M6_Pump,   1,            Pump1, 0403, 6001, 1-1.2
VICI_M6_Pump,   2,            Pump2, 0403, 6001, 1-1.3
Temperature,    1,            TC720, 0403, 6001, 1-2.1
MirrorBox,      1,            UV365, 2341, 0043, 1-3.1
DH2000,         1,            DH2000, 0403, 6015, 1-3.2
```

> VID and PID values are hexadecimal strings (4 digits, no `0x` prefix).
> `USBLocation` is the value from `p.location` reported by pyserial.

---

## Step 3: New Utility — `utils/port_resolver.py`

Create this file. It provides a single function that maps VID + PID + location
to the current COM port label.

```python
# utils/port_resolver.py

import serial.tools.list_ports


def resolve_port(vid: str, pid: str, location: str = None) -> str:
    """
    Find the COM port for a USB serial device identified by VID, PID,
    and optionally its physical USB location.

    Parameters
    ----------
    vid : str
        4-character hex string, e.g. "0403"
    pid : str
        4-character hex string, e.g. "6001"
    location : str, optional
        USB hub path from serial.tools.list_ports, e.g. "1-1.2".
        Required when multiple devices share the same VID:PID.

    Returns
    -------
    str
        Port name, e.g. "COM5" or "/dev/ttyUSB0"

    Raises
    ------
    RuntimeError
        If no matching device is found, or if multiple devices match
        and no location was provided to disambiguate.
    """
    vid_int = int(vid, 16)
    pid_int = int(pid, 16)

    all_ports = serial.tools.list_ports.comports()
    matches = [p for p in all_ports if p.vid == vid_int and p.pid == pid_int]

    if not matches:
        raise RuntimeError(
            f"No USB device found with VID={vid} PID={pid}. "
            "Check that the device is plugged in."
        )

    if location:
        location_matches = [p for p in matches if p.location == location]
        if not location_matches:
            available = [p.location for p in matches]
            raise RuntimeError(
                f"No device found with VID={vid} PID={pid} at location={location!r}. "
                f"Available locations for this VID:PID: {available}"
            )
        return location_matches[0].device

    if len(matches) > 1:
        locations = [p.location for p in matches]
        raise RuntimeError(
            f"Multiple devices share VID={vid} PID={pid}. "
            f"Add a USBLocation to the config to distinguish them. "
            f"Found at locations: {locations}"
        )

    return matches[0].device
```

---

## Step 4: Integrate into `registry_loader.py`

The current code in `methods/registry_loader.py` (lines ~122–126) reads the
`COMPort` column directly:

```python
# Current code
if "port_kwarg" in entry:
    com_port = csv_row.get("COMPort")
    if isinstance(com_port, str):
        com_port = com_port.strip() or None
    kwargs[entry["port_kwarg"]] = com_port
```

Replace this block with:

```python
# Updated code
if "port_kwarg" in entry:
    vid      = str(csv_row.get("VID",         "")).strip()
    pid      = str(csv_row.get("PID",         "")).strip()
    location = str(csv_row.get("USBLocation", "")).strip() or None

    if vid and pid:
        from utils.port_resolver import resolve_port
        com_port = resolve_port(vid, pid, location)
    else:
        com_port = None  # device has no serial port (e.g. Ocean Optics USB)

    kwargs[entry["port_kwarg"]] = com_port
```

This is the only code change required to make the system work with the new
config format.

---

## Step 5: Update the Config Builder GUI (optional but recommended)

In `utils/config_builder.py`, the `scan_ports()` method (lines ~219–244)
currently records `p.device` (the COM port label). Update it to also capture
`VID`, `PID`, and `location` so the GUI auto-fills those columns when the user
scans for devices:

```python
# In scan_ports()
ports = list(list_ports.comports())
self.available_ports = [p.device for p in ports]
self.port_info = {
    p.device: {
        "VID":         f"{p.vid:04X}" if p.vid else "",
        "PID":         f"{p.pid:04X}" if p.pid else "",
        "USBLocation": p.location or "",
        "description": p.description,
    }
    for p in ports
}
```

Then when the user selects a port in the GUI, auto-populate the VID, PID, and
USBLocation fields from `self.port_info[selected_port]` instead of storing the
COM port label.

---

## Device Registry TOML — No Changes Needed

`methods/device_registry.toml` entries use a `port_kwarg` field to indicate
what constructor argument receives the port. That stays the same — the resolver
handles finding the port; the TOML just says where to pass it.

```toml
# No changes needed — this still works as-is
[devices.VICI_M6_Pump]
port_kwarg = "port"

[devices.Temperature]
port_kwarg = "port"
```

---

## Summary of Files to Change

| File | Change |
|------|--------|
| `utils/port_resolver.py` | **Create** — new `resolve_port()` utility |
| `methods/registry_loader.py` | **Edit** — replace `COMPort` read with `resolve_port()` call (lines ~122–126) |
| `utils/config_builder.py` | **Edit** — capture VID/PID/location in `scan_ports()` (lines ~219–244) |
| All instrument config CSVs | **Update** — replace `COMPort` column with `VID`, `PID`, `USBLocation` |
| `methods/device_registry.toml` | No changes needed |
| All device implementations | No changes needed |

---

## Testing the Change

After making the changes:

1. With all instruments connected, run the discovery snippet from Step 1 to
   confirm pyserial can see each device with the expected VID, PID, and location.

2. Update the config CSV with the captured values.

3. Start an experiment normally. Watch the startup logs — instead of
   `Initialized Pump1 on COM17` you will see `Initialized Pump1 on COM5` (or
   whatever the OS assigned that session). The key is it connects without
   manual reconfiguration.

4. Unplug one instrument, replug it. Run the experiment again. It should connect
   without any config changes.

5. If you see a `RuntimeError` with "No USB device found", check:
   - Is the device powered on and plugged in?
   - Does `python -m serial.tools.list_ports -v` show it?
   - Are the VID/PID hex values in the CSV correct?

---

## Notes on Cross-Platform Behavior

| Feature | Windows | Linux |
|---------|---------|-------|
| `p.device` format | `COM5` | `/dev/ttyUSB0` |
| `p.location` format | `1-1-2` (dashes) | `1-1.2` (dots after root) |
| `p.vid` / `p.pid` | Integer or `None` | Integer or `None` |
| `p.serial_number` | Available if device exposes it | Available if device exposes it |

The `resolve_port()` function works identically on both platforms — the returned
`p.device` string is whatever the OS uses natively, so no platform-specific
handling is needed in the rest of the code.

On Linux, if `p.location` is `None` for some devices, it may be because the
kernel version or USB driver does not expose it. In that case, fall back to
serial number (if available) or accept that VID+PID alone is sufficient for
that device.
