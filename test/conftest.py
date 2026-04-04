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
    from devices.industry_components.temperature_controller.tc720.tc720 import TC720
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
    from devices.industry_components.uv_detectors.dh2000 import DH2000LightSource
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
    from devices.custom_components.light_source.mirror_box_365nm.mirror_box_365nm import MirrorBox365nm
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
    # TODO : We should have this script autodetect the COM ports
    candidates = ["COM17"] + [p.device for p in serial.tools.list_ports.comports()
                               if p.device != "COM17"]
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
    from devices.industry_components.pumps.tricontinental_c24000 import TricontinentalC24000
    pump = TricontinentalC24000(port=tricontinental_port)
    pump.connect()
    yield pump
    try:
        pump.stop()
    except Exception:
        pass
    pump.close()


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
    from devices.industry_components.temperature_controller.tc720.tc720 import TC720
    tc = TC720(port="COM_TEST")
    mock_ser = MagicMock()
    mock_ser.is_open = True
    mock_ser.read.side_effect = read_responses + [b""] * 20
    tc.ser = mock_ser
    tc._connected = True
    return tc

def make_vici_m6_response(response_str: str) -> bytes:
    """Helper to create a byte response for VICI M6 pump."""
    return (response_str + "\r").encode("ascii")


def make_vici_m6_device():
    """Return a MagicMock serial port pre-configured for VICI M6 pump unit tests."""
    mock_ser = MagicMock()
    mock_ser.is_open = True
    mock_ser.readline.return_value = make_vici_m6_response("1000.0")
    return mock_ser

def make_tricontinental_c24000_response(response_str: str) -> bytes:
    """Helper to create a byte response for Tricontinental C24000 pump."""
    return (response_str + "\r").encode("ascii")

def make_tricontinental_c24000_device():
    """Return a MagicMock serial port pre-configured for Tricontinental C24000 pump unit tests.

    read_response() reads one byte at a time until it sees the ETX byte (0x03).
    A response of b'`1\\x03' satisfies is_initialized() — the '`1' substring
    means the pump reports itself as already initialized, so connect() skips
    the initialization routine entirely and returns quickly.
    """
    mock_ser = MagicMock()
    mock_ser.is_open = True
    mock_ser.in_waiting = 0
    # Each read_response() call consumes 3 bytes: backtick, '1', ETX.
    # 50 repetitions covers all serial reads made during connect() and status checks.
    mock_ser.read.side_effect = [b'`', b'1', b'\x03'] * 50
    return mock_ser

def make_vici_valve_response(response_str: str = "OK") -> bytes:
    """Helper to create a byte response for VICI valve unit tests."""
    return (response_str + "\r\n").encode("ascii")


def make_vici_valve_device():
    """Return a MagicMock serial port pre-configured for VICI valve unit tests.

    ViciValve.__init__ calls set_number_of_positions() → send_command() → readline().
    The mock returns b'OK\\r\\n' for every readline() call.
    """
    mock_ser = MagicMock()
    mock_ser.is_open = True
    mock_ser.readline.return_value = b"OK\r\n"
    return mock_ser


def make_uv_detector_response() -> bytes:
    """Return a placeholder UV detector serial response."""
    return b"OK\r\n"


def make_uv_detector_device():
    """Return a MagicMock serial port pre-configured for UV detector unit tests."""
    mock_ser = MagicMock()
    mock_ser.is_open = True
    return mock_ser