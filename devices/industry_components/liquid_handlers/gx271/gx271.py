# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

'''
Docstring for liquid_handlers.gx271.gx271
This code provides a basic TCP client for communicating with the GX-271
liquid handler. 
'''

import socket
import time
import xml.etree.ElementTree as ET
import re
import sys
import os

try:
    from ..liquid_handlers import LiquidHandler
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from devices.industry_components.liquid_handlers.liquid_handlers import LiquidHandler

# Valid single-character motor status codes returned by the M command.
_VALID_MOTOR_CHARS = set("ERUP")


class GX271(LiquidHandler):
    DEVICE_TYPE = 'GX271'

    def __init__(self,
                 name: str,
                 uid: int = 35,
                 handshake_port: int = 50185,
                 command_port: int = 50190,
                 host: str = "192.168.8.140",
                 device_name: str = "GX-27x",
                 timeout: float = 5.0,
                 debug: bool = True,
                 ):

        self.name = name
        self.uid = uid
        self.XMIN, self.XMAX = 0, 100
        self.YMIN, self.YMAX = 0, 100
        self.ZMIN, self.ZMAX = 0, 100
        self.SAFE_Z = 110

        self.rack1 = 204
        self.rack2 = 204
        self.rack3 = 204

        self.handshake_port = handshake_port
        self.command_port = command_port
        self.host = host
        self.device_name = device_name
        self.device_id = uid
        self.timeout = timeout
        self.debug = debug
        self._sock = None
        self._seq = 0
        self._connected = False

    # ---- Connection ----------------------------------------------------------------

    def connect(self):
        hs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        hs.settimeout(self.timeout)
        hs.connect((self.host, self.handshake_port))
        hs.sendall(b"<Gilson><GilsonConnect>Gilson Ethernet Utility</GilsonConnect></Gilson>")
        time.sleep(0.3)
        hs.recv(4096)
        hs.close()

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.timeout)
        self._sock.connect((self.host, self.command_port))
        print(f"Connected to GX-271 at {self.host}:{self.command_port}")

        self._sock.settimeout(1.5)
        try:
            init = b""
            while True:
                try:
                    chunk = self._sock.recv(65536)
                    if chunk:
                        init += chunk
                    else:
                        break
                except socket.timeout:
                    break
            print(f"GX-271 Initial Status Received ({len(init)} bytes)")
        finally:
            self._sock.settimeout(self.timeout)

        self._seq += 1
        admin_xml = (
            f"<Gilson><CommandData><Commands><Command>"
            f"<CommandType>Local</CommandType>"
            f"<CommandInfo>"
            f"<InstrumentInfo><DeviceName>System</DeviceName><DeviceId>-1</DeviceId></InstrumentInfo>"
            f"<SequenceNumber>{self._seq}</SequenceNumber>"
            f"<Synchronize>True</Synchronize>"
            f"<Selected>False</Selected>"
            f"<CommandXML><CommandName>Admin</CommandName></CommandXML>"
            f"</CommandInfo>"
            f"</Command></Commands></CommandData></Gilson>"
        )
        self._sock.sendall(admin_xml.encode("utf-8"))
        lease_resp = self._recv_for_seq(self._seq, timeout=5.0)
        if "Success" in lease_resp:
            print("Lease acquired successfully.")
        elif "62" in lease_resp:
            raise RuntimeError("Failed to acquire lease: Not the lease holder.")
        else:
            print(f"Unexpected lease response: {lease_resp}")

        self._connected = True

    def disconnect(self):
        if self._sock:
            self._sock.close()
            self._sock = None
        self._connected = False

    def close(self):
        self.disconnect()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    # ---- Send/Receive Commands -----------------------------------------------------

    def _build_xml(self, gsioc_cmd: str, command_name: str, seq: int) -> str:
        return (
            f"<Gilson><CommandData><Commands><Command>"
            f"<CommandType>Local</CommandType>"
            f"<CommandInfo>"
            f"<InstrumentInfo>"
            f"<DeviceName>{self.device_name}</DeviceName>"
            f"<DeviceId>{self.device_id}</DeviceId>"
            f"</InstrumentInfo>"
            f"<SequenceNumber>{seq}</SequenceNumber>"
            f"<Synchronize>True</Synchronize>"
            f"<Selected>False</Selected>"
            f"<CommandXML>"
            f"<CommandName>{command_name}</CommandName>"
            f"<Parameters><Parameter>"
            f"<ParameterName>Command</ParameterName>"
            f"<ParameterValue>{gsioc_cmd}</ParameterValue>"
            f"</Parameter></Parameters>"
            f"</CommandXML>"
            f"</CommandInfo>"
            f"</Command></Commands></CommandData></Gilson>"
        )
    
    def _send_buffered_command(self, gsioc_cmd: str, timeout: float = None) -> dict:
        """
        Sends a motion command (H, X{pos}, Z{pos}))
        Buffered = device queues the command and returns 'Success' immediately,
        but motion may still be in progress. Always call wait_ready() after.
        """
        self._seq += 1
        seq = self._seq
        recv_timeout = timeout if timeout is not None else self.timeout
        xml = self._build_xml(gsioc_cmd, "Buffered", seq)  # BUG FIX 1: was "BufferedCommand"

        if self.debug:
            print(f"Sending Buffered: {gsioc_cmd} (seq={seq})")

        self._sock.sendall(xml.encode("utf-8"))
        response = self._recv_for_seq(seq, timeout=recv_timeout)

        if self.debug:
            print(f"Response for seq {seq}: {response}")

        result = self._parse_response(response, seq)
        self._check_response_code(result)

        if self.debug:
            print(f"  --> ResponseCode={result['ResponseCode']}  ResponseValue={result['ResponseValue']!r}")

        return result
    
    def _send_immediate_command(self, gsioc_cmd: str, timeout: float = None) -> dict:
        """
        Send a query command (M, X, Z, %, e, S, etc.).
        Immediate = device executes now and returns the actual value.
        Must NOT use Buffered for queries — Buffered only returns 'Success'.
        """
        self._seq += 1
        seq = self._seq
        recv_timeout = timeout if timeout is not None else self.timeout
        xml = self._build_xml(gsioc_cmd, "Immediate", seq)  # BUG FIX 2: was "ImmediateCommand"

        if self.debug:
            print(f"Sending Immediate: {gsioc_cmd} (seq={seq})")

        self._sock.sendall(xml.encode("utf-8"))
        response = self._recv_for_seq(seq, timeout=recv_timeout)

        if self.debug:
            print(f"Response for seq {seq}: {response}")

        result = self._parse_response(response, seq)
        self._check_response_code(result)

        if self.debug:
            print(f"  --> ResponseCode={result['ResponseCode']}  ResponseValue={result['ResponseValue']!r}")

        return result
    
    def _check_response_code(self, results: dict) -> None:
        if results.get("ResponseCode") == "69":  # BUG FIX 3: was == 69 (int); ResponseCode is always a string
            raise RuntimeError(
                f"ResponseCode=69: Device ID mismatch. "
                f"Sent DeviceId={self.device_id}. Check the unit ID selector on the rear panel."
            )
        
    def _recv_for_seq(self, seq: int, timeout: float = 5.0) -> str:  # BUG FIX 4: was = None, causing TypeError on time.time() + None
        data = b""
        deadline = time.time() + timeout
        self._sock.settimeout(0.5)
        try:
            while time.time() < deadline:
                try:
                    chunk = self._sock.recv(65536)
                    if chunk:
                        data += chunk
                except socket.timeout:
                    pass
                text = data.decode("utf-8", errors="ignore")
                seq_tag = f"<SequenceNumber>{seq}</SequenceNumber>"
                if seq_tag in text and "<Response>" in text:
                    for block in re.split(r'(?<=</Message>)', text):  # BUG FIX 5: was (?=</Message>) (lookahead)
                        if seq_tag in block and "<Response>" in block and "</Message>" in block:
                            return text
        finally:
            self._sock.settimeout(self.timeout)
        return data.decode("utf-8", errors="ignore")
    
    def _parse_response(self, response: str, seq: int) -> dict:
        result = {"raw": response, "ResponseCode": None, "ResponseValue": None, "seq": seq}

        blocks = re.split(r'(?<=</Message>)', response)  # BUG FIX 5 (continued): same lookahead→lookbehind fix
        target = response
        for block in blocks:
            if (f"<SequenceNumber>{seq}</SequenceNumber>" in block 
                and "<Response>" in block):
                target = block
                break
        if "<Message" in target:
            try:
                inner_start = target.index(">") + 1
                inner_end = target.rfind("</Message>")
                target = target[inner_start:inner_end]
            except ValueError:
                pass

        try:
            root = ET.fromstring(f"<root>{target}</root>")
            for param in root.iter("Parameter"):
                name = param.findtext("ParameterName", "")
                value = param.findtext("ParameterValue", "")
                if name == "ResponseCode":
                    result["ResponseCode"] = value
                elif name == "ResponseValue":
                    result["ResponseValue"] = value
            if not result["ResponseValue"]:
                for rp in root.iter("ReturnParameter"):
                    val = rp.findtext("ParameterValue", "")
                    if val and val not in ("-1", ""):
                        result["ResponseValue"] = val
                        break
        except ET.ParseError as e:
            result["parse_error"] = str(e)
            if self.debug:
                print(f"XML parse error: {e}")

        return result
    
    # ---- Motion Synchronisation ----------------------------------------------------

    def get_motor_status(self) -> str:
        """M (immediate) — returns per-axis chars: E=Error R=Running U=Unhomed P=Parked"""
        return self._send_immediate_command("M").get("ResponseValue", "") or ""
    
    def wait_ready(self, poll_interval: float = 0.25, timeout: float = 120.0) -> bool:
        """
        Block until all axes are idle (no R or U in motor status string).
        Error states (E) raise immediately.
        Unexpected response strings (e.g. 'Success') keep polling rather than
        incorrectly declaring motion complete.
        """
        start = time.time()
        last_status = ""
        while time.time() - start < timeout:
            last_status = self.get_motor_status()
            if self.debug:
                print(f"Motor status: '{last_status}'")
            
            is_valid = (
                last_status
                and 1 <= len(last_status) <= 3
                and all(c in _VALID_MOTOR_CHARS for c in last_status)
            )

            if not is_valid:
                time.sleep(poll_interval)
                continue

            if "E" in last_status:
                raise RuntimeError(f"Motor error detected: {last_status}")
            
            if "R" not in last_status and "U" not in last_status:
                return True
            
            time.sleep(poll_interval)

        raise TimeoutError(f"Motion timed out after {timeout}s (last status={last_status!r})")
    
    # ---- Core Movement -------------------------------------------------------------

    def home(self):
        """Home all axes. Blocks until homing completes."""
        result = self._send_buffered_command("H", timeout=30.0)
        self.wait_ready(timeout=120.0)
        return result
    
    def get_xy(self) -> tuple:
        """Get the current XY position (immediate). Returns (x, y) in mm."""
        # BUG FIX 6: method body was empty (only a docstring), always returning None
        # and causing status() to crash with TypeError on None[0].
        raw = self._send_immediate_command("X").get("ResponseValue", "") or ""
        try:
            parts = raw.split("/")
            return float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            return 0.0, 0.0

    def move_xy(self, x: float, y: float, sx: float = 350, sy: float = 350):
        """Move to XY position. Blocks until motion completes."""
        if self.get_z() < self.SAFE_Z:
            print(f"Warning: Moving XY while Z is below safe height ({self.SAFE_Z}mm)")
            self.move_z(self.SAFE_Z)
            self.wait_ready()
        result = self._send_buffered_command(f"X{x:.3f}:{sx:.1f}/{y:.3f}:{sy:.1f}", timeout=15.0)
        self.wait_ready()
        return result
    
    def get_z(self) -> float:
        """Get the current Z position in mm (immediate)."""
        raw = self._send_immediate_command("Z").get("ResponseValue", "") or ""
        try:
            return float(raw)
        except ValueError:
            return 0.0
        
    def move_z(self, z: float, sz: float = 125):
        """Move Z axis. Blocks until motion completes. Max speed 125 mm/s."""
        result = self._send_buffered_command(f"Z{z:.3f}:{sz:.1f}", timeout=15.0)
        self.wait_ready()
        return result
    
    def identity(self) -> str:
        """% (immediate) — firmware version string e.g. 'GX 271 v1.2.2'"""
        return self._send_immediate_command("%").get("ResponseValue", "")
    
    def get_safe_z_height(self) -> float:
        """Return the safe Z height (mm) for the liquid handler."""
        return self.SAFE_Z
    
    # ---- Misc/Status ---------------------------------------------------------------

    def status(self) -> dict:
        """Return a dict with current position."""
        x, y = self.get_xy()
        z = self.get_z()
        return {"x": x, "y": y, "z": z}
    
    def _ensure_conn(self) -> None:
        if not self._connected:
            raise RuntimeError("GX-271 is not connected. Call connect() first.")    
'''
if __name__ == "__main__":
    gx = GX271(name="GX-271", uid=35, debug=True)
    gx.connect()

    gx._send_immediate_command("e")  # Clear any existing errors

    gx.home()
    gx.move_xy(150, 100)
    print("What is the z-height?", gx.get_z())
    gx.move_z(90)
    print(gx.get_xy())
    print("What is the z-height?", gx.get_z())
    gx.move_z(100)
    print("What is the z-height?", gx.get_z())
    gx.move_xy(50, 50)
    print("What is the x-y position?", gx.get_xy())
    gx.move_xy(50, 100)
    gx.move_xy(150, 50)
    gx.home()


    print(gx.status())
    gx.disconnect()
'''