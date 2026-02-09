# status_monitor_gui.py
# ------------------------------------------------------------------------------
# Standalone live status monitor window for AUTO_ZAHRT
# ------------------------------------------------------------------------------

from __future__ import annotations

import os
import re
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Optional

import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Instrument group helpers (same logic as in main GUI)
LIQUID_HANDLER_TYPES = {"GX281", "Ender3_Liquid_Handler"}
PUMP_TYPES = {"VICI_M6_Pump", "Isametic", "PhdUltraPump", "Tricontinental_C24000"}
VALVE_TYPES = {"Valve6Way", "Valve10Way", "Valve24Way"}
TEMP_TYPES = {"Temperature"}
DH2000_TYPES = {"DH2000"}
OCEANOPTICS_TYPES = {"OceanOptics_UVVis"}


def group_for_instrument_type(inst_type: str) -> Optional[str]:
    if inst_type in LIQUID_HANDLER_TYPES:
        return "LiquidHandler"
    if inst_type in PUMP_TYPES:
        return "Pump"
    if inst_type in VALVE_TYPES:
        return "Valve"
    if inst_type in TEMP_TYPES:
        return "Temperature"
    if inst_type in DH2000_TYPES:
        return "DH2000"
    if inst_type in OCEANOPTICS_TYPES:
        return "OceanOptics"
    return None


class StatusMonitorWindow(tk.Toplevel):
    """
    Separate Tkinter window that live-plots instrument status_log CSV:
      - X-axis: Elapsed_Time_s
      - Pumps/syringe pumps: flow rate on upper plot
      - Temperature controllers: temperature on lower plot
    """

    def __init__(
        self,
        master: tk.Misc,
        status_log_path: str,
        instrument_types: Dict[str, str],
        update_interval_ms: int = 60_000,  # 1 minute default
    ) -> None:
        super().__init__(master)
        self.title("AUTO_ZAHRT – Live Status Monitor")
        self.geometry("800x500")

        self.status_log_path = status_log_path
        self.instrument_types = dict(instrument_types)
        self.update_interval_ms = update_interval_ms

        self._auto_update_job: Optional[str] = None
        self._auto_update_active: bool = False

        self._build_ui()

        # Ensure proper cleanup
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start auto-update after window is fully ready (delay until mainloop starts)
        self.after(500, self.start_auto_update)

    # ────────────────────────── UI setup
    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=6)

        ttk.Label(
            top,
            text=f"Monitoring file:\n{self.status_log_path}",
            justify="left",
        ).pack(side=tk.LEFT, padx=(0, 10))

        btn_frame = ttk.Frame(top)
        btn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(btn_frame, text="Update Now", command=self.update_plot)\
            .pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Start Auto-Update", command=self.start_auto_update)\
            .pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Stop Auto-Update", command=self.stop_auto_update)\
            .pack(side=tk.LEFT, padx=4)

        # Figure + axes
        fig = Figure(figsize=(7, 3.5), dpi=100)
        ax1 = fig.add_subplot(211)
        ax2 = fig.add_subplot(212, sharex=ax1)

        ax1.set_ylabel("Flow rate (µL/min)")
        ax2.set_ylabel("Temperature (°C)")
        ax2.set_xlabel("Elapsed time (s)")

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        self._fig = fig
        self._ax_pump = ax1
        self._ax_temp = ax2
        self._canvas = canvas

    # ────────────────────────── helpers
    def _extract_first_float(self, s: str) -> Optional[float]:
        if not isinstance(s, str):
            return None
        m = re.search(r"[-+]?\d*\.?\d+", s)
        if not m:
            return None
        try:
            return float(m.group(0))
        except Exception:
            return None

    # ────────────────────────── plotting
    def update_plot(self) -> None:
        if not os.path.exists(self.status_log_path):
            messagebox.showwarning(
                "Status log missing",
                f"Status log file not found:\n{self.status_log_path}",
                parent=self,
            )
            return

        try:
            df = pd.read_csv(self.status_log_path)
        except Exception as e:
            messagebox.showerror(
                "Read error",
                f"Could not read status log:\n{e}",
                parent=self,
            )
            return

        if "Elapsed_Time_s" not in df.columns:
            messagebox.showerror(
                "Format error",
                "Status log is missing 'Elapsed_Time_s' column.",
                parent=self,
            )
            return

        x = df["Elapsed_Time_s"].values

        self._ax_pump.clear()
        self._ax_temp.clear()

        self._ax_pump.set_ylabel("Flow rate (µL/min)")
        self._ax_temp.set_ylabel("Temperature (°C)")
        self._ax_temp.set_xlabel("Elapsed time (s)")

        pump_labels = []
        temp_labels = []

        # Device columns: everything after Timestamp, Elapsed_Time_s
        for col in df.columns[2:]:
            comp_name = col
            inst_type = self.instrument_types.get(comp_name, "")
            grp = group_for_instrument_type(inst_type) if inst_type else None

            values = df[col].apply(self._extract_first_float)
            mask = values.notna()
            if not mask.any():
                continue

            x_valid = df.loc[mask, "Elapsed_Time_s"].values
            y_valid = values[mask].values

            if grp == "Pump":
                self._ax_pump.plot(x_valid, y_valid)
                pump_labels.append(comp_name)
            elif grp == "Temperature":
                self._ax_temp.plot(x_valid, y_valid)
                temp_labels.append(comp_name)

        if pump_labels:
            self._ax_pump.legend(pump_labels, fontsize="small", loc="best")
        if temp_labels:
            self._ax_temp.legend(temp_labels, fontsize="small", loc="best")

        self._fig.tight_layout()
        self._canvas.draw_idle()

    # ────────────────────────── auto-update
    def start_auto_update(self) -> None:
        # Stop any existing auto-update first
        self.stop_auto_update()
        
        self._auto_update_active = True

        def tick():
            if not self._auto_update_active:
                self._auto_update_job = None
                return
            self.update_plot()
            if self._auto_update_active:  # Check again after update
                self._auto_update_job = self.after(self.update_interval_ms, tick)

        self._auto_update_job = self.after(100, tick)  # Small delay to let UI settle

    def stop_auto_update(self) -> None:
        self._auto_update_active = False
        if self._auto_update_job is not None:
            try:
                self.after_cancel(self._auto_update_job)
            except Exception:
                pass
            self._auto_update_job = None

    # ────────────────────────── lifecycle
    def _on_close(self) -> None:
        self.stop_auto_update()
        self.destroy()


def open_status_monitor(
    master: tk.Misc,
    status_log_path: str,
    instrument_types: Dict[str, str],
    update_interval_ms: int = 60_000,
) -> StatusMonitorWindow:
    """
    Convenience function to open the status monitor window
    from your main GUI.

    Usage:
        from status_monitor_gui import open_status_monitor
        ...
        open_status_monitor(self, self.current_status_log_path, self.instrument_types)
    """
    return StatusMonitorWindow(
        master=master,
        status_log_path=status_log_path,
        instrument_types=instrument_types,
        update_interval_ms=update_interval_ms,
    )
