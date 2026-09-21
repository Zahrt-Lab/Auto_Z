# command_table_panel.py
# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Andrew Zahrt
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

from __future__ import annotations

import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class CommandTablePanel(ttk.Frame):
    """Treeview table of queued commands with export/load/clear controls."""

    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent)
        self.app = app
        self._build()
        app.command_table_panel = self

    def _build(self) -> None:
        cols = ("Component", "Action", "Parameters", "Delay", "Notes")
        self.app.tree = ttk.Treeview(self, columns=cols, show="headings", height=10)
        for c in cols:
            self.app.tree.heading(c, text=c)
            self.app.tree.column(c, anchor="center", stretch=True)
        self.app.tree.pack(fill=tk.BOTH, expand=True)

        bf = ttk.Frame(self)
        bf.pack(pady=4)
        ttk.Button(bf, text="Generate CSV", command=self._export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(bf, text="Load CSV", command=self._load_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(bf, text="Clear", command=self._clear_commands).pack(side=tk.LEFT, padx=5)

    def _export_csv(self) -> None:
        if not self.app.commands:
            return messagebox.showwarning("No commands", "Add commands first")
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Component", "Action", "Parameters", "Notes", "delay"])
            writer.writeheader()
            writer.writerows(self.app.commands)
        self.app.generated_csv_path = path
        messagebox.showinfo("Saved", f"Saved commands to:\n{path}")

    def _load_csv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))

        self.app.commands.clear()
        for iid in self.app.tree.get_children():
            self.app.tree.delete(iid)

        for r in rows:
            try:
                d = float(r.get("delay", 0.5))
            except Exception:
                d = 0.5
            cmd = {
                "Component": r.get("Component", ""),
                "Action": r.get("Action", ""),
                "Parameters": r.get("Parameters", ""),
                "delay": d,
                "Notes": r.get("Notes", ""),
            }
            self.app.commands.append(cmd)
            self.app.tree.insert("", tk.END, values=(cmd["Component"], cmd["Action"], cmd["Parameters"], d, cmd["Notes"]))

        self.app.generated_csv_path = path
        messagebox.showinfo("Loaded", f"Loaded commands from:\n{path}")

    def _clear_commands(self) -> None:
        self.app.commands.clear()
        for iid in self.app.tree.get_children():
            self.app.tree.delete(iid)
        self.app.generated_csv_path = None
