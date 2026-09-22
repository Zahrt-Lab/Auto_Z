# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from methods.registry_loader import (
    get_group as group_for_instrument_type,
    get_actions,
    get_param_fields,
)


class CommandBuilderPanel(ttk.Frame):
    """Form for selecting a component/action and adding a command to the queue."""

    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent)
        self.app = app
        self.app.param_entries = {}
        self._build()
        app.command_builder_panel = self

    def _build(self) -> None:
        frame = ttk.LabelFrame(self, text="Add Command")
        frame.pack(fill=tk.X)

        ttk.Label(frame, text="Component:").grid(row=0, column=0, sticky=tk.W)
        self.app.comp_var = tk.StringVar()
        self.app.comp_cb = ttk.Combobox(frame, textvariable=self.app.comp_var, state="readonly", width=24)
        self.app.comp_cb.bind("<<ComboboxSelected>>", self._on_component_change)
        self.app.comp_cb.grid(row=0, column=1, padx=3)

        ttk.Label(frame, text="Action:").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.app.act_var = tk.StringVar()
        self.app.act_cb = ttk.Combobox(frame, textvariable=self.app.act_var, state="readonly", width=28)
        self.app.act_cb.bind("<<ComboboxSelected>>", self._rebuild_param_fields)
        self.app.act_cb.grid(row=0, column=3, padx=3)

        self.app.param_frame = ttk.Frame(frame)
        self.app.param_frame.grid(row=1, column=0, columnspan=4, pady=(8, 0), sticky=tk.W)

        ttk.Label(frame, text="Delay (s):").grid(row=2, column=0, sticky=tk.W)
        self.app.delay_entry = ttk.Entry(frame, width=10)
        self.app.delay_entry.insert(0, "0.5")
        self.app.delay_entry.grid(row=2, column=1, sticky=tk.W)

        ttk.Label(frame, text="Notes:").grid(row=3, column=0, sticky=tk.W)
        self.app.notes_entry = ttk.Entry(frame, width=72)
        self.app.notes_entry.grid(row=3, column=1, columnspan=3, pady=(0, 6), sticky=tk.W)

        ttk.Button(frame, text="Add Command", command=self._add_command).grid(row=4, column=0, columnspan=4, pady=4)

    def _refresh_component_dropdown(self) -> None:
        """Called by FileSelectorPanel after instrument definitions are loaded."""
        self.app.comp_cb.unbind("<<ComboboxSelected>>")
        self.app.comp_cb["values"] = self.app.components
        if self.app.components:
            self.app.comp_var.set(self.app.components[0])
        self.app.comp_cb.bind("<<ComboboxSelected>>", self._on_component_change)
        if self.app.components:
            self._on_component_change()

    def _group_for_component(self, comp: str) -> Optional[str]:
        if comp == "SYNC":
            return "SYNC"
        inst_type = self.app.instrument_types.get(comp)
        if inst_type is None:
            return None
        return group_for_instrument_type(inst_type)

    def _on_component_change(self, event=None) -> None:
        if self.app._updating_component:
            return
        self.app._updating_component = True
        try:
            if event:
                idx = self.app.comp_cb.current()
                if idx >= 0:
                    self.app.comp_var.set(self.app.comp_cb["values"][idx])

            comp = self.app.comp_var.get()
            grp = self._group_for_component(comp)

            if grp is None:
                self.app.act_cb["values"] = []
                self.app.act_var.set("")
                self._rebuild_param_fields()
                return

            actions = get_actions(grp)
            self.app.act_cb["values"] = actions
            if actions:
                self.app.act_var.set(actions[0])
            else:
                self.app.act_var.set("")
            self._rebuild_param_fields()
        finally:
            self.app._updating_component = False

    def _rebuild_param_fields(self, event=None) -> None:
        if event:
            idx = self.app.act_cb.current()
            if idx >= 0:
                self.app.act_var.set(self.app.act_cb["values"][idx])

        for w in self.app.param_frame.winfo_children():
            w.destroy()
        self.app.param_entries.clear()

        comp, act = self.app.comp_var.get(), self.app.act_var.get()
        grp = self._group_for_component(comp)
        if grp is None or not act:
            return

        fields = get_param_fields(grp, act)
        for row, (key, label) in enumerate(fields):
            ttk.Label(self.app.param_frame, text=f"{label}:").grid(row=row, column=0, sticky=tk.W)
            ent = ttk.Entry(self.app.param_frame, width=28)
            ent.grid(row=row, column=1, padx=(6, 20), sticky=tk.W)
            self.app.param_entries[key] = ent

            if key in ("apply_to_device", "stop_upon_convergence"):
                ent.insert(0, "True" if key == "apply_to_device" else "False")

    def _add_command(self) -> None:
        comp, act = self.app.comp_var.get(), self.app.act_var.get()
        if not comp or not act:
            return messagebox.showerror("Input error", "Select component & action")

        try:
            delay = float(self.app.delay_entry.get())
        except ValueError:
            return messagebox.showerror("Input error", "Delay must be numeric")

        required_missing = []
        for k, ent in self.app.param_entries.items():
            if k == "name":
                continue
            if ent.get().strip() == "":
                required_missing.append(k)
        if required_missing:
            return messagebox.showerror("Input error", f"Fill all required parameters: {', '.join(required_missing)}")

        params = ",".join(f"{k}={e.get().strip()}" for k, e in self.app.param_entries.items() if e.get().strip() != "")
        notes = self.app.notes_entry.get().strip()

        cmd = {"Component": comp, "Action": act, "Parameters": params, "Notes": notes, "delay": delay}
        self.app.commands.append(cmd)
        self.app.tree.insert("", tk.END, values=(comp, act, params, delay, notes))

        for w in self.app.param_frame.winfo_children():
            w.destroy()
        self.app.param_entries.clear()
        self.app.notes_entry.delete(0, tk.END)
