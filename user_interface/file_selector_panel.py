# file_selector_panel.py
# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

from __future__ import annotations

import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from user_interface.instrument_csv_builder import launch_instrument_csv_builder


class FileSelectorPanel(ttk.Frame):
    """File path inputs and instrument config loading."""

    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent)
        self.app = app
        self._build()
        app.file_selector_panel = self

    def _build(self) -> None:
        # Files & Output row
        file_frame = ttk.LabelFrame(self, text="Files & Output")
        file_frame.pack(fill=tk.X)

        ttk.Label(file_frame, text="Instrument Config CSV:").grid(row=0, column=0, sticky=tk.W)
        self.app.config_entry = ttk.Entry(file_frame, width=60)
        self.app.config_entry.grid(row=0, column=1, padx=6, pady=2)

        ttk.Button(file_frame, text="Browse…", command=self._browse_config).grid(row=0, column=2, padx=4)
        ttk.Button(file_frame, text="Build…", command=self._open_instrument_builder).grid(row=0, column=3, padx=(0, 4))

        ttk.Label(file_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W)
        self.app.output_entry = ttk.Entry(file_frame, width=60)
        self.app.output_entry.grid(row=1, column=1, padx=6, pady=2)
        ttk.Button(file_frame, text="Browse…", command=self._browse_output).grid(row=1, column=2, padx=4)

        ttk.Label(file_frame, text="Status interval (s):").grid(row=0, column=4, sticky=tk.W, padx=(16, 0))
        self.app.status_interval_entry = ttk.Entry(file_frame, width=10)
        self.app.status_interval_entry.insert(0, "60")
        self.app.status_interval_entry.grid(row=0, column=5, padx=(6, 0))

        # Control files row
        ctrl_frame = ttk.LabelFrame(self, text="Control files (for STOP behavior)")
        ctrl_frame.pack(fill=tk.X, pady=(6, 0))

        ttk.Label(ctrl_frame, text="Instrument control file:").grid(row=0, column=0, sticky=tk.W)
        self.app.instrument_control_entry = ttk.Entry(ctrl_frame, width=60)
        self.app.instrument_control_entry.insert(0, "instrument_control.txt")
        self.app.instrument_control_entry.grid(row=0, column=1, padx=6, pady=2, sticky=tk.W)

        ttk.Label(ctrl_frame, text="DH2000 control file:").grid(row=1, column=0, sticky=tk.W)
        self.app.dh2000_control_entry = ttk.Entry(ctrl_frame, width=60)
        self.app.dh2000_control_entry.insert(0, "dh2000_light_source_control.txt")
        self.app.dh2000_control_entry.grid(row=1, column=1, padx=6, pady=2, sticky=tk.W)

        ttk.Label(ctrl_frame, text="(Write False to instrument control file to request stop.)").grid(
            row=0, column=2, rowspan=2, padx=(16, 0), sticky=tk.W
        )

    def _browse_config(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if path:
            self.app.config_entry.delete(0, tk.END)
            self.app.config_entry.insert(0, path)
            self._load_instrument_definitions(path)

    def _browse_output(self) -> None:
        d = filedialog.askdirectory()
        if d:
            self.app.output_entry.delete(0, tk.END)
            self.app.output_entry.insert(0, d)

    def _open_instrument_builder(self) -> None:
        def _on_save(path: str) -> None:
            self.app.config_entry.delete(0, tk.END)
            self.app.config_entry.insert(0, path)
            self._load_instrument_definitions(path)
            try:
                self.app.lift()
                self.app.focus_force()
            except Exception:
                pass

        launch_instrument_csv_builder(master=self.app, on_save=_on_save)

    def _load_instrument_definitions(self, path: str) -> None:
        try:
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    raise ValueError("CSV has no headers.")
                if "InstrumentType" not in reader.fieldnames or "DeviceNumber" not in reader.fieldnames:
                    raise ValueError("InstrumentType and DeviceNumber headers required.")

                self.app.instrument_types.clear()
                self.app.components.clear()

                for row in reader:
                    inst_type = row.get("InstrumentType", "").strip()
                    dev_num = str(row.get("DeviceNumber", "")).strip()
                    if not inst_type or not dev_num:
                        continue
                    component_name = f"{inst_type}_{dev_num}"
                    self.app.instrument_types[component_name] = inst_type
                    self.app.components.append(component_name)

                if "SYNC" not in self.app.components:
                    self.app.components.append("SYNC")

                self.app.components.sort()
                self.app.command_builder_panel._refresh_component_dropdown()
        except Exception as e:
            messagebox.showerror("Instrument config error", str(e))
