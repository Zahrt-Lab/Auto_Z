# schedule_run_panel.py
# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

from __future__ import annotations

import os
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from methods import GeneralExperimentMethod  # type: ignore


class ScheduleRunPanel(ttk.Frame):
    """Scheduled and immediate experiment run controls."""

    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent)
        self.app = app
        self._build()
        app.schedule_run_panel = self

    def _build(self) -> None:
        frame = ttk.LabelFrame(self, text="Schedule & Run")
        frame.pack(fill=tk.X)

        ttk.Label(frame, text="Run at (YYYY-MM-DD HH:MM:SS):").grid(row=0, column=0, sticky=tk.W)
        self.app.datetime_entry = ttk.Entry(frame, width=25)
        self.app.datetime_entry.grid(row=0, column=1, padx=6)

        ttk.Button(frame, text="Schedule experiment", command=self._schedule_run).grid(row=0, column=2, padx=6)
        ttk.Button(frame, text="Run now", command=self._run_now).grid(row=0, column=3)

    def _schedule_run(self) -> None:
        s = self.app.datetime_entry.get().strip()
        if not s:
            return messagebox.showerror("Input error", "Enter date & time")
        try:
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return messagebox.showerror("Input error", "Use YYYY-MM-DD HH:MM:SS")
        delta = (dt - datetime.now()).total_seconds()
        if delta < 0:
            return messagebox.showerror("Input error", "Time is in the past")
        messagebox.showinfo("Scheduled", f"Starts in {delta:.1f} s")
        self.app.after(int(delta * 1000), self._run_now)

    def _run_now(self) -> None:
        if not self.app.generated_csv_path:
            return messagebox.showerror("Missing file", "Generate or load a method CSV first")
        if not self.app.config_entry.get().strip():
            return messagebox.showerror("Missing file", "Select instrument-config CSV")

        out = self.app.output_entry.get().strip() or os.getcwd()
        Path(out).mkdir(parents=True, exist_ok=True)

        threading.Thread(target=self._run_experiment_thread, args=(out,), daemon=True).start()

    def _run_experiment_thread(self, out_dir: str) -> None:
        self.app._append_log("Starting experiment…\n")
        try:
            try:
                status_interval = int(float(self.app.status_interval_entry.get().strip()))
            except Exception:
                status_interval = 60

            exp = GeneralExperimentMethod(
                input_file=self.app.generated_csv_path,
                instrument_config_file=self.app.config_entry.get(),
                output_dir=out_dir,
                output_file="AUTO_ZAHRT_Run",
                status_interval=status_interval,
                instrument_control_file=self.app.instrument_control_entry.get().strip() or "instrument_control.txt",
                dh2000_light_source_control_file=self.app.dh2000_control_entry.get().strip() or "dh2000_light_source_control.txt",
            )

            self.app.current_status_log_path = getattr(exp, "status_log_filename", None)
            self.app.current_instrument_control_file_path = getattr(exp, "instrument_control_file", "instrument_control.txt")
            self.app.current_dh2000_control_file_path = getattr(exp, "dh2000_light_source_control_file", "dh2000_light_source_control.txt")
            self.app.current_experiment_instruments = getattr(exp, "instruments", None)

            orig_log = exp.log_to_csv

            def patched(comp, act, params, output, notes=""):
                orig_log(comp, act, params, output, notes)
                self.app._append_log(f"[{comp}] {act} – {output}" + (f" ({notes})" if notes else "") + "\n")

            exp.log_to_csv = patched  # type: ignore[attr-defined]
            exp.run_experiment()

            self.app._append_log("\nExperiment finished.\n")
            self.app.after(0, lambda: messagebox.showinfo("Done", "Experiment finished"))
        except Exception as e:
            self.app._append_log(f"\n[ERROR] {e}\n")
            error_msg = str(e)
            self.app.after(0, lambda msg=error_msg: messagebox.showerror("Error", msg))
