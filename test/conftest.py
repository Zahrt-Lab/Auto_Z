"""
Shared pytest fixtures for AUTO_ZAHRT test suite.

Hardware fixtures auto-detect connected devices by scanning COM ports.
If a device is not found, hardware tests are skipped automatically —
no manual configuration required.
"""

import os
import time
from typing import Optional
import pytest
import serial
import serial.tools.list_ports
from unittest.mock import MagicMock

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


def _detect_dh2000_port() -> Optional[str]:
    """
    Scan all available COM ports for a DH2000 Arduino TTL controller.
    Opens each port at 9600 baud, sends 's' (status command), and checks
    the response for the expected DH2000 status format ('Shutter:').
    Returns the first matching port, or None if not found.
    """
    for port_info in serial.tools.list_ports.comports():
        port = port_info.device
        ser = None
        try:
            ser = serial.Serial(port, baudrate=9600, timeout=2.0)
            time.sleep(2.0)           # Wait for Arduino reset after connect
            if ser.in_waiting > 0:
                ser.read(ser.in_waiting)  # Drain startup messages
            time.sleep(0.5)
            ser.write(b"s")           # DH2000 status command (no newline)
            time.sleep(0.3)
            response = ""
            for _ in range(5):        # Read up to 5 lines
                line = ser.readline().decode("utf-8", errors="ignore")
                response += line
                if "Shutter:" in response:
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
def dh2000_port() -> Optional[str]:
    """
    Detect the COM port of a connected DH2000 Arduino TTL controller.
    Skips the entire hardware test session if no device is found.
    """
    port = _detect_dh2000_port()
    if port is None:
        pytest.skip("DH2000 not detected on any COM port — skipping hardware tests")
    return port


@pytest.fixture(scope="session")
def dh2000_device(dh2000_port: str):
    """
    Connected DH2000LightSource instance, shared across the hardware test session.
    Performs a safe_shutdown on teardown to leave the device in a known safe state.
    """
    from uv_detectors.dh2000 import DH2000LightSource
    dh = DH2000LightSource(port=dh2000_port, baudrate=9600, timeout=2.0)
    dh.connect()
    yield dh
    try:
        dh.safe_shutdown()   # Safe: shutter closed, lamps off before disconnecting
    except Exception:
        pass
    dh.close()


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


# ---------------------------------------------------------------------------
# Tricontinental C24000 fixtures
# ---------------------------------------------------------------------------

def _detect_tricontinental_port() -> Optional[str]:
    """
    Try COM17 first (known port), then scan all ports at 9600 baud.
    Sends a status query to pump address 1 and checks for the ETX byte (0x03)
    that the Tricontinental firmware appends to every response.
    Returns the matching port, or None if not found.
    """
    candidates = ["COM25"] + [p.device for p in serial.tools.list_ports.comports()
                               if p.device != "COM25"]
    for port in candidates:
        ser = None
        try:
            ser = serial.Serial(port, baudrate=9600,
                                bytesize=serial.EIGHTBITS,
                                parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE,
                                timeout=2)
            time.sleep(2)
            if ser.in_waiting:
                ser.read(ser.in_waiting)  # drain startup bytes
            ser.reset_input_buffer()
            ser.write("/1?\r".encode("utf-8"))
            ser.flush()
            response = ser.read(64)       # read up to 64 bytes
            if b'\x03' in response:       # ETX = pump found
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
def tricontinental_port() -> Optional[str]:
    """
    Detect the COM port of a connected Tricontinental C24000 pump.
    Skips the entire hardware test session if no device is found.
    """
    port = _detect_tricontinental_port()
    if port is None:
        pytest.skip("Tricontinental C24000 not detected on any COM port — skipping hardware tests")
    return port


@pytest.fixture(scope="session")
def tricontinental_device(tricontinental_port: str):
    """
    Connected TricontinentalC24000 instance, shared across the hardware test session.
    Stops both pumps and closes the port cleanly on teardown.
    """
    from pumps.tricontinental_c24000 import TricontinentalC24000
    pump = TricontinentalC24000(port=tricontinental_port)
    pump.connect()
    yield pump
    try:
        pump.stop()
    except Exception:
        pass
    pump.close()


# ---------------------------------------------------------------------------
# VICI M6 pump fixtures
# ---------------------------------------------------------------------------

def _detect_vici_m6_port() -> Optional[str]:
    """Detect VICI M6 pump by probing each COM port with a velocity query."""
    preferred_ports = ["COM16", "COM4", "COM21"]
    # Preserve preferred ordering, then try every remaining port once.
    remaining = [p.device for p in serial.tools.list_ports.comports()
                 if p.device not in preferred_ports]
    candidates = preferred_ports + remaining
    for port in candidates:
        ser = None
        try:
            ser = serial.Serial(port, baudrate=9600, timeout=1.0)
            time.sleep(0.2)
            if ser.in_waiting:
                ser.read(ser.in_waiting)
            ser.reset_input_buffer()
            ser.write(b"PR V\r")
            ser.flush()
            response = ser.readline().decode("utf-8", errors="ignore").strip()
            if not response:
                continue
            try:
                float(response)
                return port
            except ValueError:
                continue
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
def vici_m6_port() -> Optional[str]:
    """Detect the COM port of a connected VICI M6 pump."""
    port = _detect_vici_m6_port()
    if port is None:
        pytest.skip("VICI M6 pump not detected on any COM port — skipping hardware tests")
    return port


@pytest.fixture(scope="session")
def vici_m6_device(vici_m6_port: str):
    """Connected VICI_M6_Pumps instance shared across hardware tests."""
    from pumps.vici_m6_pump.vici_m6_pump import VICI_M6_Pumps

    pump = VICI_M6_Pumps(port=vici_m6_port)
    if pump.ser is None:
        pytest.skip("Unable to open serial connection to VICI M6 pump")
    pump.start()
    yield pump
    try:
        pump.stop()
    except Exception:
        pass
    try:
        pump.stop_connection()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# VICI valve fixtures
# ---------------------------------------------------------------------------

def _detect_vici_valve_port() -> Optional[str]:
    """Detect a VICI valve by issuing a CP (current position) query."""
    preferred_ports = ["COM15", "COM5", "COM18"]
    remaining = [p.device for p in serial.tools.list_ports.comports()
                 if p.device not in preferred_ports]
    candidates = preferred_ports + remaining
    for port in candidates:
        ser = None
        try:
            ser = serial.Serial(port, baudrate=9600, timeout=1.0)
            time.sleep(0.2)
            if ser.in_waiting:
                ser.read(ser.in_waiting)
            ser.reset_input_buffer()
            ser.write(b"CP\r")
            ser.flush()
            response = ser.readline().decode("utf-8", errors="ignore").strip()
            if not response:
                continue
            normalized = response.upper().replace("CP", "").replace("P", "")
            normalized = normalized.replace("=", "").strip()
            if normalized.isdigit():
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
def vici_valve_port() -> Optional[str]:
    """Detect the COM port of a connected VICI valve."""
    port = _detect_vici_valve_port()
    if port is None:
        pytest.skip("VICI valve not detected on any COM port — skipping hardware tests")
    return port


@pytest.fixture(scope="session")
def vici_valve_device(vici_valve_port: str):
    """Connected ViciValve instance shared across hardware tests."""
    from valves.vici_valves.vici_valves import ViciValve

    valve_type = os.getenv("VICI_VALVE_TYPE", "10-way")
    valve = ViciValve(port=vici_valve_port, valve_type=valve_type)
    try:
        valve.connect()
    except Exception:
        pass
    yield valve
    try:
        valve.move_home()
    except Exception:
        pass
    valve.close()


# ---------------------------------------------------------------------------
# Shared TC720 test helpers (used by unit and integration tests)
# ---------------------------------------------------------------------------

def make_tc720_response(temp_celsius: float) -> bytes:
    """Build a valid 8-byte TC720 response for a given temperature."""
    val = int(temp_celsius * 100)
    if val < 0:
        val += 0x10000
    dddd = format(val, '04x')
    checksum = format(sum(ord(c) for c in dddd) & 0xFF, '02x')
    return ('*' + dddd + checksum + '\r').encode('ascii')


def make_tc720_device(read_responses: list):
    """TC720 with mock serial pre-loaded with read() responses."""
    from temperature_controller.tc720.tc720 import TC720
    tc = TC720(port="COM_TEST")
    mock_ser = MagicMock()
    mock_ser.is_open = True
    mock_ser.read.side_effect = read_responses + [b""] * 20
    tc.ser = mock_ser
    tc._connected = True
    return tc
