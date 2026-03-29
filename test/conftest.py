"""
Shared pytest fixtures for AUTO_ZAHRT test suite.

Hardware fixtures auto-detect connected devices by scanning COM ports.
If a device is not found, hardware tests are skipped automatically —
no manual configuration required.
"""

import time
from typing import Optional
import pytest
import serial
import serial.tools.list_ports


# ---------------------------------------------------------------------------
# COM port auto-detection
# ---------------------------------------------------------------------------

def _detect_mirror_box_port() -> Optional[str]:
    """
    Scan all available COM ports for a MirrorBox365nm Arduino.
    Opens each port at 9600 baud, sends 's', and checks the response
    for the expected status format ('Light1:' and 'DimmerPWM:').
    Returns the first matching port, or None if not found.
    """
    for port_info in serial.tools.list_ports.comports():
        port = port_info.device
        ser = None
        try:
            ser = serial.Serial(port, baudrate=9600, timeout=1.5)
            time.sleep(2.0)           # Wait for Arduino reset after connect
            if ser.in_waiting > 0:
                ser.read(ser.in_waiting)  # Drain startup messages
            time.sleep(0.5)
            ser.write(b"s\n")
            time.sleep(0.3)
            response = ser.read(ser.in_waiting).decode("utf-8", errors="ignore")
            if "Light1:" in response and "DimmerPWM:" in response:
                return port
        except (serial.SerialException, OSError):
            continue
        finally:
            if ser is not None:
                try:
                    ser.close()
                except Exception:
                    pass
    return None


# ---------------------------------------------------------------------------
# Session-scoped fixtures (connect once, shared across all hardware tests)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def mirror_box_port() -> Optional[str]:
    """
    Detect the COM port of a connected MirrorBox365nm.
    Skips the entire hardware test session if no device is found.
    """
    port = _detect_mirror_box_port()
    if port is None:
        pytest.skip("MirrorBox365nm not detected on any COM port — skipping hardware tests")
    return port


@pytest.fixture(scope="session")
def mirror_box_device(mirror_box_port: str):
    """
    Connected MirrorBox365nm instance, shared across the hardware test session.
    Dims to 255 (off) and closes cleanly on teardown.
    """
    from custom_components.light_source.mirror_box_365nm.mirror_box_365nm import MirrorBox365nm
    mb = MirrorBox365nm(port=mirror_box_port)
    mb.connect()
    yield mb
    try:
        mb.set_dimmer(255)   # Safe: dim to off before disconnecting
    except Exception:
        pass
    mb.close()
