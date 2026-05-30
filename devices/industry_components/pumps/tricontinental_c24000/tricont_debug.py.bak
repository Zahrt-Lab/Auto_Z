
# ------------------------------------------------------------------------------
# Diagnostic Script: Tricontinental C24000 Pump B Initialization Failure
# Run this to identify why Pump B is not initializing.
# ------------------------------------------------------------------------------

import sys
import time
sys.path.insert(0, r"C:\Users\zahrtlab\Documents\test\Auto_Zahrt_v3")  # adjust if needed

import devices.industry_components.pumps.tricontinental_c24000.tricont_pyserial as tri

PORT    = "COM25"
BAUD    = 9600
PUMP    = "B"          # the problem pump
PUMP_ADDR = 2          # address for pump B

# ── low-level helpers ─────────────────────────────────────────────────────────

def raw_query(ser, pump_addr: int, cmd: str, label: str) -> str:
    """Send a raw command and return the decoded response."""
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    full = f"/{pump_addr}{cmd}\r"
    ser.write(full.encode())
    ser.flush()
    time.sleep(0.15)
    try:
        resp = tri.read_response(ser)
    except TimeoutError as e:
        resp = f"TIMEOUT: {e}"
    print(f"  [{label}]  TX: {full.strip()!r}   RX: {resp!r}")
    return resp

def decode_status_byte(resp: str) -> dict:
    """
    Parse the status character out of a pump response.
    The status byte is the character immediately after '/0'.
    Bit 5 = 1 → idle, Bit 5 = 0 → busy
    Bits 0-3 = error code
    """
    # Find the status character – it follows '/0'
    try:
        idx = resp.index("/0") + 2
        ch = resp[idx]
    except (ValueError, IndexError):
        return {"raw": resp, "status_char": "?", "busy": "?",
                "error_code": "?", "error_desc": "unknown"}

    val = ord(ch)
    busy   = not bool(val & 0x20)   # bit 5
    err    = val & 0x0F             # bits 0-3

    ERROR_DESCRIPTIONS = {
        0:  "No error",
        1:  "Initialization failure",
        2:  "Invalid command",
        3:  "Invalid operand",
        4:  "Invalid checksum",
        5:  "Unused",
        6:  "EEPROM failure",
        7:  "Device not initialized",
        8:  "CAN bus failure",
        9:  "Plunger overload",
        10: "Valve overload",
        11: "Plunger move not allowed",
        15: "Command overflow",
    }

    return {
        "raw":        resp.strip(),
        "status_char": ch,
        "busy":       busy,
        "error_code": err,
        "error_desc": ERROR_DESCRIPTIONS.get(err, f"Unknown ({err})"),
    }

def print_status(label: str, resp: str):
    d = decode_status_byte(resp)
    busy_str  = "BUSY" if d["busy"] else "IDLE"
    print(f"    → {label}: status={d['status_char']!r}  "
          f"pump={busy_str}  err={d['error_code']} ({d['error_desc']})")
    return d

# ── diagnostic steps ──────────────────────────────────────────────────────────

def step(n: str, title: str):
    print(f"\n{'─'*60}")
    print(f"  STEP {n}: {title}")
    print(f"{'─'*60}")

def run_diagnostics():
    print("=" * 60)
    print(f"  Tricontinental C24000 — Pump {PUMP} Diagnostic")
    print("=" * 60)

    ser = tri.connect(port=PORT, baudrate=BAUD)
    print(f"\nConnected on {PORT} @ {BAUD} baud\n")

    # ------------------------------------------------------------------
    step("1", "Basic comms check — firmware query (?)")
    resp = raw_query(ser, PUMP_ADDR, "?", "status query")
    d = print_status("Current state", resp)

    # ------------------------------------------------------------------
    step("2", "Check error register explicitly (Q)")
    resp = raw_query(ser, PUMP_ADDR, "Q", "Q command")
    d = print_status("Error register", resp)

    # ------------------------------------------------------------------
    step("3", "Check initialization flag (?19)")
    resp = raw_query(ser, PUMP_ADDR, "?19", "init flag")
    initialized = "`1" in resp
    print(f"    → Initialized: {initialized}   (raw: {resp.strip()!r})")

    # ------------------------------------------------------------------
    step("4", "Check current plunger position (?)")
    resp = raw_query(ser, PUMP_ADDR, "?0", "plunger position")
    print(f"    → Plunger position response: {resp.strip()!r}")

    # ------------------------------------------------------------------
    step("5", "Check valve position (?6)")
    resp = raw_query(ser, PUMP_ADDR, "?6", "valve position")
    valve_out = "o" in resp
    print(f"    → Valve at output: {valve_out}   (raw: {resp.strip()!r})")

    # ------------------------------------------------------------------
    step("6", "Attempt STOP command (T) — clear any in-progress motion")
    resp = raw_query(ser, PUMP_ADDR, "T", "terminate")
    print_status("After stop", resp)
    time.sleep(1)

    # ------------------------------------------------------------------
    step("7", "Re-check error register after stop (Q)")
    resp = raw_query(ser, PUMP_ADDR, "Q", "Q after stop")
    d = print_status("Error after stop", resp)

    # ------------------------------------------------------------------
    step("8", "Try a slow initialization (V1000ZR) — N0 mode, slow speed")
    print("  Sending: V1000ZR  (slow init, watching for 20 s...)")
    resp = raw_query(ser, PUMP_ADDR, "V1000ZR", "slow init")
    print_status("Init command response", resp)

    for i in range(8):
        time.sleep(2.5)
        resp = raw_query(ser, PUMP_ADDR, "?19", f"init poll {i+1}/8")
        d = print_status(f"  Poll {i+1}", resp)
        initialized = "`1" in resp
        if initialized:
            print("  ✓ Pump B initialized successfully with slow speed!")
            break
        if d["error_code"] == 1:
            print("  ✗ Initialization failure error — plunger likely physically blocked.")
            break
        if d["error_code"] == 9:
            print("  ✗ Plunger overload — motor stalled. Physical obstruction confirmed.")
            break
    else:
        print("  ✗ Pump B did not initialize within timeout.")

    # ------------------------------------------------------------------
    step("9", "Final status summary")
    resp_q   = raw_query(ser, PUMP_ADDR, "Q",   "final Q")
    resp_i19 = raw_query(ser, PUMP_ADDR, "?19", "final ?19")
    resp_v   = raw_query(ser, PUMP_ADDR, "?6",  "final valve")
    print_status("Final error register", resp_q)
    print(f"    → Initialized flag: {'YES' if '`1' in resp_i19 else 'NO'}")
    print(f"    → Valve at output:  {'YES' if 'o' in resp_v else 'NO'}")

    # ------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("  Diagnostic complete. Review STEP 8 results:")
    print("    • If pump initialized → it was a speed issue, use V1000ZR")
    print("    • If error_code=9 (overload) → physical jam confirmed")
    print("    • If error_code=1 (init fail) → plunger blocked or drive fault")
    print("    • If still idle/no error → possible wiring/address issue")
    print(f"{'='*60}\n")

    ser.close()

if __name__ == "__main__":
    run_diagnostics()