# control_bar_panel.py
# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

try:
    from utils.status import open_status_monitor as open_csv_status_monitor  # type: ignore
except Exception:
    open_csv_status_monitor = None

try:
    from utils.status_monitor_gui import open_status_monitor as open_live_status_monitor  # type: ignore
except Exception:
    open_live_status_monitor = None


class ControlBarPanel(ttk.Frame):
    """Emergency stop button, status monitor launchers, and run history shortcut."""

    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent)
        self.app = app
        self._build()
        app.control_bar_panel = self

    def _build(self) -> None:
        self.app.emergency_button = tk.Button(
            self,
            text="EMERGENCY STOP",
            command=self._emergency_stop,
            bg="#cc0000",
            fg="white",
            activebackground="#990000",
            activeforeground="white",
            relief=tk.RAISED,
            padx=10,
            pady=4,
        )
        self.app.emergency_button.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(self, text="Open Status Log Plots", command=self._open_status_monitor).pack(side=tk.LEFT, padx=5)
        ttk.Button(self, text="Open Live Device Status", command=self._open_live_device_status).pack(side=tk.LEFT, padx=5)

    def _emergency_stop(self) -> None:
        path = self.app.current_instrument_control_file_path or self.app.instrument_control_entry.get().strip() or "instrument_control.txt"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("False")
            self.app._append_log(f"[CONTROL] Wrote 'False' to {path} (stop requested).\n")
            messagebox.showinfo("Emergency stop", f"Stop signal written to:\n{path}")
        except Exception as e:
            messagebox.showerror("Stop error", f"Could not write to control file:\n{e}")

    def _open_status_monitor(self) -> None:
        if not self.app.current_status_log_path:
            return messagebox.showwarning("No status log", "No status log file available yet. Start an experiment first.")
        if open_csv_status_monitor is None:
            return messagebox.showwarning("Unavailable", "utils.status.open_status_monitor not found in this environment.")
        if self.app.status_window is None or not self.app.status_window.winfo_exists():
            self.app.status_window = open_csv_status_monitor(
                self.app,
                self.app.current_status_log_path,
                self.app.instrument_types,
                update_interval_ms=60_000,
            )
        else:
            self.app.status_window.lift()
            self.app.status_window.focus_force()

    def _open_live_device_status(self) -> None:
        if not self.app.current_experiment_instruments:
            return messagebox.showwarning("No instruments", "No active experiment with instruments. Start an experiment first.")
        if open_live_status_monitor is None:
            return messagebox.showwarning("Unavailable", "utils.status_monitor_gui.open_status_monitor not found.")
        if self.app.live_status_window is None or not self.app.live_status_window.winfo_exists():
            self.app.live_status_window = open_live_status_monitor(self.app.current_experiment_instruments, interval=5)
        else:
            self.app.live_status_window.lift()
            self.app.live_status_window.focus_force()

