from __future__ import annotations

import os
import tkinter as tk
from status import open_status_monitor

if __name__ == "__main__":
    """
    Run a standalone status monitor for quick testing.

    Usage examples:
        python -m utils.status --status-log path/to/log.csv
        python -m utils.status

    If no status log is provided, a tiny sample CSV will be created in the
    system temporary directory and used for demonstration.
    """
    import argparse
    import tempfile
    import csv
    import time

    parser = argparse.ArgumentParser(description="Run status monitor (standalone)")
    parser.add_argument("--status-log", dest="status_log", help="Path to status CSV")
    parser.add_argument("--interval-ms", dest="interval_ms", type=int, default=5000,
                        help="Auto-update interval in milliseconds (default: 10000 = 10s)")
    args = parser.parse_args()

    status_path = args.status_log
    if not status_path:
        # Create a small sample CSV for demo purposes
        tmp = tempfile.gettempdir()
        status_path = os.path.join(tmp, "status_monitor_sample.csv")
        if not os.path.exists(status_path):
            now = int(time.time())
            rows = [
                (now + i, i * 10, f"{i*0.5} uL/min", f"{25.0 + i*0.1} C")
                for i in range(10)
            ]
            with open(status_path, "w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["Timestamp", "Elapsed_Time_s", "Pump1", "Temp1"])
                for r in rows:
                    writer.writerow(r)

    # Auto-detect instrument types from column names
    # Expected columns after Timestamp and Elapsed_Time_s
    import pandas as pd
    
    instrument_types = {}
    try:
        df = pd.read_csv(status_path, nrows=0)  # Read just headers
        for col in df.columns[2:]:  # Skip Timestamp and Elapsed_Time_s
            col_lower = col.lower()
            # Auto-detect based on common naming patterns
            if any(x in col_lower for x in ["pump", "vici_m6", "isametic", "phd"]):
                # Assign appropriate pump type based on name
                if "isametic" in col_lower or "isamatic" in col_lower:
                    instrument_types[col] = "Isametic"
                elif "phd" in col_lower:
                    instrument_types[col] = "PhdUltraPump"
                elif "vici" in col_lower or "m6" in col_lower:
                    instrument_types[col] = "VICI_M6_Pump"
                else:
                    instrument_types[col] = "VICI_M6_Pump"  # Default pump type
            elif "temp" in col_lower:
                instrument_types[col] = "Temperature"
            elif "valve" in col_lower or "vici" in col_lower:
                if "6" in col or "6way" in col_lower:
                    instrument_types[col] = "Valve6Way"
                elif "10" in col or "10way" in col_lower:
                    instrument_types[col] = "Valve10Way"
                elif "24" in col or "24way" in col_lower:
                    instrument_types[col] = "Valve24Way"
                else:
                    instrument_types[col] = "Valve6Way"
            elif any(x in col_lower for x in ["gx281", "gx-281", "ender3", "liquid"]):
                if "ender" in col_lower:
                    instrument_types[col] = "Ender3_Liquid_Handler"
                else:
                    instrument_types[col] = "GX281"
        
        if not instrument_types:
            # Fallback for demo CSV
            instrument_types = {"Pump1": "VICI_M6_Pump", "Temp1": "Temperature"}
    except Exception as e:
        print(f"Warning: Could not auto-detect instrument types: {e}")
        instrument_types = {"Pump1": "VICI_M6_Pump", "Temp1": "Temperature"}

    root = tk.Tk()
    root.withdraw()  # keep the root window hidden; monitor is a Toplevel

    win = open_status_monitor(
        master=root,
        status_log_path=status_path,
        instrument_types=instrument_types,
        update_interval_ms=args.interval_ms,
    )

    win.mainloop()
