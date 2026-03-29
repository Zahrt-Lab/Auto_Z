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

# Sensor-1 query for TC720: '*01000021\r' (pre-computed, see test_tc720_parsing.py)
_TC720_PROBE_QUERY = b'*01000021\r'


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

def _detect_tc720_port() -> Optional[str]:
    """
    Scan all available COM ports for a TC720 temperature controller.
    Opens each port at 230400 baud, sends a sensor-1 query, and checks
    for a valid 8-byte response starting with '*'.
    Returns the first matching port, or None if not found.
    """
    for port_info in serial.tools.list_ports.comports():
        port = port_info.device
        ser = None
        try:
            ser = serial.Serial(port, baudrate=230400, timeout=1)
            ser.reset_input_buffer()
            ser.write(_TC720_PROBE_QUERY)
            ser.flush()
            time.sleep(0.1)
            resp = ser.read(8)
            if len(resp) == 8 and resp[0:1] == b'*':
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


@pytest.fixture(scope="session")
def tc720_port() -> Optional[str]:
    """
    Detect the COM port of a connected TC720 temperature controller.
    Skips the entire hardware test session if no device is found.
    """
    port = _detect_tc720_port()
    if port is None:
        pytest.skip("TC720 not detected on any COM port — skipping hardware tests")
    return port


@pytest.fixture(scope="session")
def tc720_device(tc720_port: str):
    """
    Connected TC720 instance, shared across the hardware test session.
    Returns temperature to 25°C (safe default) and closes cleanly on teardown.
    """
    from temperature_controller.tc720.tc720 import TC720
    tc = TC720(port=tc720_port)
    tc.connect()
    yield tc
    try:
        tc.set_temperature(25.0)   # Return to safe temperature before disconnecting
    except Exception:
        pass
    tc.close()


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
