# auto_zahrt_gui.py (for example)
# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

from __future__ import annotations

import csv
import glob
import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Optional, Callable, Dict

# Third-party
import pandas as pd

# AUTO_ZAHRT imports
# Add project root to path for imports
try:
    # Get the project root (parent of methods/ directory)
    project_root = Path(__file__).parent.parent.resolve()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
except Exception:
    pass

try:
    from methods import GeneralExperimentMethod
except ModuleNotFoundError:
    print("ERROR: Cannot import GeneralExperimentMethod. Check your PYTHONPATH.")
    raise

# Import the CSV plotting status monitor
from utils.status import open_status_monitor as open_csv_status_monitor, group_for_instrument_type
# Import the text-based live instrument monitor
from utils.status_monitor_gui import open_status_monitor as open_live_status_monitor

# ──────────────────────────────────────────────────────────────────────────────
# Embedded Instrument CSV Builder (unchanged interface)

COLUMNS = ("InstrumentType", "DeviceNumber", "Name", "COMPort", "OtherParams")

INSTRUMENT_CHOICES = [
    "GX281",
    "Ender3_Liquid_Handler",
    "VICI_M6_Pump",
    "Isametic",
    "PhdUltraPump",
    "Valve6Way",
    "Valve10Way",
    "Valve24Way",
    "Temperature",
]

DEFAULT_ROWS = [
    ("GX281",       "1", "GX-281",       "COM2",  ""),
    ("VICI_M6_Pump","1", "Pump",         "COM17", ""),
    ("Isametic",    "1", "IsameticPump", "COM4",  ""),
    ("Valve6Way",   "1", "VICI-6Way",    "COM7",  ""),
    ("Valve6Way",   "2", "VICI-6Way",    "COM11", ""),
    ("Valve24Way",  "1", "VICI-24Way",   "COM13", ""),
    ("Valve24Way",  "2", "VICI-24Way",   "COM14", ""),
    ("Temperature", "1", "Temperature",  "COM12", ""),
]


class InstrumentCSVBuilder(tk.Toplevel):
    def __init__(self, master: tk.Misc | None, on_save: Optional[Callable[[str], None]] = None) -> None:
        super().__init__(master)
        self.title("Instrument CSV Builder")
        self.geometry("1000x600")
        self.minsize(760, 420)
        self.resizable(True, True)

        self._on_save = on_save
        self.last_path: Optional[str] = None

        wrap = ttk.Frame(self)
        wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        toolbar = ttk.Frame(wrap)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(toolbar, text="Open CSV…", command=self._open_csv).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Save as CSV…", command=self._save_csv).pack(side=tk.LEFT)
        ttk.Separator(toolbar, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(toolbar, text="Add Row", command=self._add_row).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Duplicate Row", command=self._dup_row).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Delete Row(s)", command=self._del_row).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Close", command=self.destroy).pack(side=tk.RIGHT)

        self.tree = ttk.Treeview(wrap, columns=COLUMNS, show="headings", height=16)
        for c in COLUMNS:
            self.tree.heading(c, text=c)
            if c in ("OtherParams", "Name"):
                self.tree.column(c, anchor="w", width=260, stretch=True)
            elif c == "InstrumentType":
                self.tree.column(c, anchor="center", width=160, stretch=False)
            elif c == "COMPort":
                self.tree.column(c, anchor="center", width=120, stretch=False)
            else:
                self.tree.column(c, anchor="center", width=120, stretch=False)
        self.tree.pack(fill=tk.BOTH, expand=True)

        for row in DEFAULT_ROWS:
            self.tree.insert("", tk.END, values=row)

        ttk.Label(
            wrap,
            text="Tip: Double-click a cell to edit. InstrumentType is a dropdown; DeviceNumber is numeric.",
        ).pack(fill=tk.X, pady=(8, 4))
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status).pack(fill=tk.X, padx=10, pady=(0, 8))

        self.tree.bind("<Double-1>", self._on_double_click)

        try:
            ttk.Style().theme_use("clam")
        except tk.TclError:
            pass

        self.transient(master)
        self.grab_set()
        self.focus()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _selected_row(self) -> Optional[str]:
        sel = self.tree.selection()
        return sel[0] if sel else None

    def _add_row(self) -> None:
        self.tree.insert("", tk.END, values=("GX281", "1", "New Instrument", "COM1", ""))
        self.status.set("Added a new row.")

    def _dup_row(self) -> None:
        iid = self._selected_row()
        if not iid:
            self.status.set("Select a row to duplicate.")
            return
        vals = self.tree.item(iid, "values")
        self.tree.insert("", tk.END, values=vals)
        self.status.set("Duplicated row.")

    def _del_row(self) -> None:
        sel = self.tree.selection()
        if not sel:
            self.status.set("Select row(s) to delete.")
            return
        for iid in sel:
            self.tree.delete(iid)
        self.status.set("Deleted selected row(s).")

    def _on_double_click(self, event) -> None:
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return

        bbox = self.tree.bbox(row_id, col_id)
        if not bbox:
            return
        x, y, w, h = bbox
        col_index = int(col_id.replace("#", "")) - 1
        col_name = COLUMNS[col_index]
        old_val = self.tree.set(row_id, col_name)

        def finish(new_val: str) -> None:
            self.tree.set(row_id, col_name, new_val)
            widget.destroy()

        if col_name == "InstrumentType":
            widget = ttk.Combobox(self.tree, values=INSTRUMENT_CHOICES, state="readonly")
            widget.place(x=x, y=y, width=w, height=h)
            widget.set(old_val if old_val in INSTRUMENT_CHOICES else INSTRUMENT_CHOICES[0])
            widget.focus_set()
            widget.bind("<<ComboboxSelected>>", lambda *_: finish(widget.get()))
            widget.bind("<Return>", lambda *_: finish(widget.get()))
            widget.bind("<Escape>", lambda *_: widget.destroy())

        elif col_name == "DeviceNumber":
            sv = tk.StringVar(value=old_val if old_val.isdigit() else "1")
            widget = ttk.Spinbox(self.tree, from_=1, to=999, textvariable=sv, wrap=False)
            widget.place(x=x, y=y, width=w, height=h)
            widget.focus_set()
            widget.select_range(0, tk.END)
            widget.bind("<Return>", lambda *_: finish(widget.get()))
            widget.bind("<FocusOut>", lambda *_: finish(widget.get()))
            widget.bind("<Escape>", lambda *_: widget.destroy())

        else:
            widget = ttk.Entry(self.tree)
            widget.place(x=x, y=y, width=w, height=h)
            widget.insert(0, old_val)
            widget.select_range(0, tk.END)
            widget.focus_set()
            widget.bind("<Return>", lambda *_: finish(widget.get().strip()))
            widget.bind("<FocusOut>", lambda *_: finish(widget.get().strip()))
            widget.bind("<Escape>", lambda *_: widget.destroy())

    def _validate_rows(self, rows):
        for i, (itype, dev, name, com, other) in enumerate(rows, start=1):
            if itype.strip() == "" or itype not in INSTRUMENT_CHOICES:
                messagebox.showerror("Validation error", f"Row {i}: invalid InstrumentType.")
                return False
            if not dev.strip().isdigit() or int(dev) <= 0:
                messagebox.showerror("Validation error", f"Row {i}: DeviceNumber must be a positive integer.")
                return False
            if name.strip() == "":
                messagebox.showerror("Validation error", f"Row {i}: Name cannot be empty.")
                return False
            if com.strip() == "":
                messagebox.showerror("Validation error", f"Row {i}: COMPort cannot be empty.")
                return False
        return True

    def _collect_rows(self):
        return [tuple(self.tree.item(iid, "values")) for iid in self.tree.get_children("")]

    def _save_csv(self) -> None:
        rows = self._collect_rows()
        if not rows:
            messagebox.showwarning("No rows", "Add at least one row before saving.")
            return
        if not self._validate_rows(rows):
            return

        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return

        try:
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(COLUMNS))
                writer.writeheader()
                for r in rows:
                    writer.writerow({c: v for c, v in zip(COLUMNS, r)})
            self.last_path = path
            messagebox.showinfo("Saved", f"Saved CSV to:\n{path}")
            if callable(self._on_save):
                self._on_save(path)
        except Exception as e:
            messagebox.showerror("Save error", str(e))

    def _open_csv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        try:
            with open(path, "r", newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None or [*reader.fieldnames] != list(COLUMNS):
                    messagebox.showerror(
                        "Open error",
                        "CSV headers must be exactly:\n" + ", ".join(COLUMNS),
                    )
                    return
                for iid in self.tree.get_children(""):
                    self.tree.delete(iid)
                for row in reader:
                    vals = tuple(row.get(c, "") for c in COLUMNS)
                    self.tree.insert("", tk.END, values=vals)
            self.last_path = path
            self.status.set(f"Loaded {path}")
        except Exception as e:
            messagebox.showerror("Open error", str(e))


def launch_instrument_csv_builder(
    master: tk.Misc | None = None,
    on_save: Optional[Callable[[str], None]] = None,
) -> None:
    if master is None:
        root = tk.Tk()
        root.withdraw()
        dlg = InstrumentCSVBuilder(root, on_save=on_save)
        root.mainloop()
    else:
        InstrumentCSVBuilder(master, on_save=on_save)


# ──────────────────────────────────────────────────────────────────────────────
# Command/action mapping

ACTIONS_BY_GROUP: dict[str, list[str]] = {
    "LiquidHandler": ["set_bedlayout", "move_home", "move_z_height", "move_xy", "move_z"],
    "Pump": ["aspirate", "dispense"],
    "Valve": ["go_to_position", "move_home"],
    "Temperature": ["set_temperature", "get_temperature", "wait_convergence"],
    "SYNC": ["wait_for_pumps"],
}

PARAM_FIELDS: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("LiquidHandler", "set_bedlayout"): [("bed", "Bed"), ("rack_layout", "Rack Layout")],
    ("LiquidHandler", "move_z_height"): [("height", "Height (Z)")],
    ("LiquidHandler", "move_xy"): [("bed", "Bed"), ("well", "Well")],
    ("LiquidHandler", "move_z"): [("bed", "Bed"), ("well", "Well")],

    ("Pump", "aspirate"): [("flow_rate", "Flow rate (µL/min)"), ("volume", "Volume (µL)")],
    ("Pump", "dispense"): [("flow_rate", "Flow rate (µL/min)"), ("volume", "Volume (µL)")],

    ("Valve", "go_to_position"): [("position", "Position")],
    ("Valve", "move_home"): [],

    ("Temperature", "set_temperature"): [("temp", "Temperature (°C)")],
    ("Temperature", "get_temperature"): [],
    ("Temperature", "wait_convergence"): [
        ("target_temp", "Target (°C)"),
        ("tolerance", "Tolerance (±°C)"),
        ("duration", "Stable time (s)"),
    ],

    ("SYNC", "wait_for_pumps"): [],
}

# ──────────────────────────────────────────────────────────────────────────────
# Main GUI

class AutoZahrtGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AUTO_ZAHRT – Scheduler & Runner")
        self.geometry("1100x820")

        self.commands: list[dict[str, str | float]] = []
        self.param_entries: dict[str, ttk.Entry] = {}
        self.generated_csv_path: str | None = None

        self.instrument_types: Dict[str, str] = {}  # component -> InstrumentType
        self.components: list[str] = []

        self.current_status_log_path: Optional[str] = None
        self.current_control_file_path: str = "control.txt"
        self.current_experiment_instruments: Optional[Dict[str, Any]] = None

        self.run_history: list[dict[str, str]] = []

        self.status_window = None  # the CSV plotting monitor window
        self.live_status_window = None  # the text-based live instrument monitor window

        self._build_file_selector()
        self._build_command_entry()
        self._build_command_tree()
        self._build_schedule_section()
        self._build_control_bar()  # <-- buttons placed here
        self._build_log_panel()
        self._build_history_panel()

    # ────────────────────────── FILE SELECTION
    def _build_file_selector(self) -> None:
        frame = ttk.LabelFrame(self, text="Files & Output")
        frame.pack(fill=tk.X, padx=10, pady=6)

        ttk.Label(frame, text="Instrument Config CSV:") \
            .grid(row=0, column=0, sticky=tk.W)
        self.config_entry = ttk.Entry(frame, width=60)
        self.config_entry.grid(row=0, column=1, padx=6, pady=2)

        ttk.Button(frame, text="Browse…", command=self._browse_config) \
            .grid(row=0, column=2, padx=4)

        ttk.Button(
            frame, text="Build…", command=self._open_instrument_builder
        ).grid(row=0, column=3, padx=(0, 4))

        ttk.Label(frame, text="Output Directory:") \
            .grid(row=1, column=0, sticky=tk.W)
        self.output_entry = ttk.Entry(frame, width=60)
        self.output_entry.grid(row=1, column=1, padx=6, pady=2)
        ttk.Button(frame, text="Browse…", command=self._browse_output) \
            .grid(row=1, column=2, padx=4)

        ttk.Button(
            frame,
            text="Open UV-Vis Detector…",
            command=self._open_uvvis_gui
        ).grid(row=0, column=4, rowspan=2, padx=(16, 4))

    def _browse_config(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if path:
            self.config_entry.delete(0, tk.END)
            self.config_entry.insert(0, path)
            self._load_instrument_definitions(path)

    def _browse_output(self) -> None:
        d = filedialog.askdirectory()
        if d:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, d)
            self._refresh_history_from_fs()

    def _open_instrument_builder(self) -> None:
        def _on_save(path: str) -> None:
            self.config_entry.delete(0, tk.END)
            self.config_entry.insert(0, path)
            self._load_instrument_definitions(path)
            try:
                self.lift()
                self.focus_force()
            except Exception:
                pass

        launch_instrument_csv_builder(master=self, on_save=_on_save)

    def _load_instrument_definitions(self, path: str) -> None:
        try:
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    raise ValueError("CSV has no headers.")
                if "InstrumentType" not in reader.fieldnames or "DeviceNumber" not in reader.fieldnames:
                    raise ValueError("InstrumentType and DeviceNumber headers required.")
                self.instrument_types.clear()
                self.components.clear()
                for row in reader:
                    inst_type = row.get("InstrumentType", "").strip()
                    dev_num = str(row.get("DeviceNumber", "")).strip()
                    if not inst_type or not dev_num:
                        continue
                    component_name = f"{inst_type}_{dev_num}"
                    self.instrument_types[component_name] = inst_type
                    self.components.append(component_name)

                if "SYNC" not in self.components:
                    self.components.append("SYNC")

                self.components.sort()
                self.comp_cb["values"] = self.components
                if self.components:
                    self.comp_cb.current(0)
                    self._on_component_change()
        except Exception as e:
            messagebox.showerror("Instrument config error", str(e))

    # ────────────────────────── COMMAND BUILDER
    def _build_command_entry(self) -> None:
        frame = ttk.LabelFrame(self, text="Add Command")
        frame.pack(fill=tk.X, padx=10, pady=6)

        ttk.Label(frame, text="Component:") \
            .grid(row=0, column=0, sticky=tk.W)
        self.comp_var = tk.StringVar()
        self.comp_cb = ttk.Combobox(
            frame, textvariable=self.comp_var,
            state="readonly", width=24
        )
        self.comp_cb.bind("<<ComboboxSelected>>", self._on_component_change)
        self.comp_cb.grid(row=0, column=1, padx=3)

        ttk.Label(frame, text="Action:") \
            .grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.act_var = tk.StringVar()
        self.act_cb = ttk.Combobox(
            frame, textvariable=self.act_var,
            state="readonly", width=24
        )
        self.act_cb.bind("<<ComboboxSelected>>", self._rebuild_param_fields)
        self.act_cb.grid(row=0, column=3, padx=3)

        self.param_frame = ttk.Frame(frame)
        self.param_frame.grid(row=1, column=0, columnspan=4, pady=(8, 0), sticky=tk.W)

        ttk.Label(frame, text="Delay (s):") \
            .grid(row=2, column=0, sticky=tk.W)
        self.delay_entry = ttk.Entry(frame, width=10)
        self.delay_entry.insert(0, "0.5")
        self.delay_entry.grid(row=2, column=1, sticky=tk.W)

        ttk.Label(frame, text="Notes:") \
            .grid(row=3, column=0, sticky=tk.W)
        self.notes_entry = ttk.Entry(frame, width=60)
        self.notes_entry.grid(row=3, column=1, columnspan=3, pady=(0, 6), sticky=tk.W)

        ttk.Button(frame, text="Add Command", command=self._add_command) \
            .grid(row=4, column=0, columnspan=4, pady=4)

    def _group_for_component(self, comp: str) -> Optional[str]:
        if comp == "SYNC":
            return "SYNC"
        inst_type = self.instrument_types.get(comp)
        if inst_type is None:
            return None
        return group_for_instrument_type(inst_type)

    def _on_component_change(self, _=None) -> None:
        comp = self.comp_var.get()
        grp = self._group_for_component(comp)
        if grp is None:
            self.act_cb["values"] = []
            self.act_var.set("")
            self._rebuild_param_fields()
            return
        actions = ACTIONS_BY_GROUP.get(grp, [])
        self.act_cb["values"] = actions
        if actions:
            self.act_cb.current(0)
        self._rebuild_param_fields()

    def _rebuild_param_fields(self, _=None) -> None:
        for w in self.param_frame.winfo_children():
            w.destroy()
        self.param_entries.clear()
        comp, act = self.comp_var.get(), self.act_var.get()
        grp = self._group_for_component(comp)
        if grp is None or not act:
            return
        fields = PARAM_FIELDS.get((grp, act), [])
        for row, (key, label) in enumerate(fields):
            ttk.Label(self.param_frame, text=f"{label}:") \
                .grid(row=row, column=0, sticky=tk.W)
            ent = ttk.Entry(self.param_frame, width=16)
            ent.grid(row=row, column=1, padx=(4, 20), sticky=tk.W)
            self.param_entries[key] = ent

    def _add_command(self) -> None:
        comp, act = self.comp_var.get(), self.act_var.get()
        if not comp or not act:
            return messagebox.showerror("Input error", "Select component & action")

        try:
            delay = float(self.delay_entry.get())
        except ValueError:
            return messagebox.showerror("Input error", "Delay must be numeric")

        if any(e.get().strip() == "" for e in self.param_entries.values()):
            return messagebox.showerror("Input error", "Fill all parameters")

        params = ",".join(f"{k}={e.get().strip()}" for k, e in self.param_entries.items())
        notes = self.notes_entry.get().strip()
        cmd = {"Component": comp, "Action": act, "Parameters": params, "delay": delay, "Notes": notes}
        self.commands.append(cmd)
        self.tree.insert("", tk.END, values=(comp, act, params, delay, notes))

        for w in self.param_frame.winfo_children():
            w.destroy()
        self.param_entries.clear()
        self.notes_entry.delete(0, tk.END)

    # ────────────────────────── COMMAND TABLE
    def _build_command_tree(self) -> None:
        cols = ("Component", "Action", "Parameters", "Delay", "Notes")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor="center", stretch=True)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        bf = ttk.Frame(self)
        bf.pack(pady=4)
        ttk.Button(bf, text="Generate CSV", command=self._export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(bf, text="Load CSV", command=self._load_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(bf, text="Clear", command=self._clear_commands).pack(side=tk.LEFT, padx=5)

    def _export_csv(self) -> None:
        if not self.commands:
            return messagebox.showwarning("No commands", "Add commands first")
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["Component", "Action", "Parameters", "Notes", "delay"])
            writer.writeheader()
            writer.writerows(self.commands)
        self.generated_csv_path = path
        messagebox.showinfo("Saved", f"Saved commands to {path}")

    def _load_csv(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
        self.commands.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
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
            self.commands.append(cmd)
            self.tree.insert(
                "", tk.END,
                values=(cmd["Component"], cmd["Action"], cmd["Parameters"], d, cmd["Notes"])
            )
        self.generated_csv_path = path
        messagebox.showinfo("Loaded", f"Loaded commands from {path}")

    def _clear_commands(self) -> None:
        self.commands.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.generated_csv_path = None

    # ────────────────────────── SCHEDULE & RUN
    def _build_schedule_section(self) -> None:
        frame = ttk.LabelFrame(self, text="Schedule & Run")
        frame.pack(fill=tk.X, padx=10, pady=6)
        ttk.Label(frame, text="Run at (YYYY-MM-DD HH:MM:SS):") \
            .grid(row=0, column=0, sticky=tk.W)
        self.datetime_entry = ttk.Entry(frame, width=25)
        self.datetime_entry.grid(row=0, column=1, padx=6)
        ttk.Button(frame, text="Schedule experiment", command=self._schedule_run) \
            .grid(row=0, column=2, padx=6)
        ttk.Button(frame, text="Run now", command=self._run_now) \
            .grid(row=0, column=3)

    def _schedule_run(self) -> None:
        s = self.datetime_entry.get().strip()
        if not s:
            return messagebox.showerror("Input error", "Enter date & time")
        try:
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return messagebox.showerror("Input error", "Use YYYY-MM-DD HH:MM:SS")
        delta = (dt - datetime.now()).total_seconds()
        if delta < 0:
            return messagebox.showerror("Input error", "Time is in the past")
        messagebox.showinfo("Scheduled", f"Starts in {delta:.1f}s")
        self.after(int(delta * 1000), self._run_now)

    def _run_now(self) -> None:
        if not self.generated_csv_path:
            return messagebox.showerror("Missing file", "Generate or load a CSV first")
        if not self.config_entry.get().strip():
            return messagebox.showerror("Missing file", "Select instrument-config CSV")
        out = self.output_entry.get().strip() or os.getcwd()
        Path(out).mkdir(parents=True, exist_ok=True)
        threading.Thread(target=self._run_experiment_thread, args=(out,), daemon=True).start()

    def _run_experiment_thread(self, out_dir: str) -> None:
        self._append_log("Starting experiment…\n")
        try:
            exp = GeneralExperimentMethod(
                input_file=self.generated_csv_path,
                instrument_config_file=self.config_entry.get(),
                output_dir=out_dir,
                output_file="AUTO_ZAHRT_Run",
            )

            self.current_status_log_path = exp.status_log_filename
            self.current_control_file_path = exp.control_file
            self.current_experiment_instruments = exp.instruments  # Store reference to instruments

            orig_log = exp.log_to_csv

            def patched(comp, act, params, output, notes=""):
                orig_log(comp, act, params, output, notes)
                self._append_log(f"[{comp}] {act} – {output} ({notes})\n")

            exp.log_to_csv = patched  # type: ignore
            exp.run_experiment()

            self._register_run(exp)

            self._append_log("\nExperiment finished successfully.\n")
            messagebox.showinfo("Done", "Experiment finished")
        except Exception as e:
            self._append_log(f"\n[ERROR] {e}\n")
            messagebox.showerror("Error", str(e))

    # ────────────────────────── CONTROL BAR (ABOVE LOG)
    def _build_control_bar(self) -> None:
        frame = ttk.Frame(self)
        frame.pack(fill=tk.X, padx=10, pady=(4, 0))

        # Big red emergency stop
        self.emergency_button = tk.Button(
            frame,
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
        self.emergency_button.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(frame, text="Open Status Log Plots", command=self._open_status_monitor)\
            .pack(side=tk.LEFT, padx=5)

        ttk.Button(frame, text="Open Live Device Status", command=self._open_live_device_status)\
            .pack(side=tk.LEFT, padx=5)

        ttk.Button(frame, text="Run History", command=self._show_run_history)\
            .pack(side=tk.LEFT, padx=5)

    def _emergency_stop(self) -> None:
        path = self.current_control_file_path or "control.txt"
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("False")
            self._append_log(f"[CONTROL] Wrote 'False' to {path} (emergency stop requested).\n")
            messagebox.showinfo("Emergency stop", f"Stop signal written to:\n{path}")
        except Exception as e:
            messagebox.showerror("Stop error", f"Could not write to control file:\n{e}")

    def _open_status_monitor(self) -> None:
        """Open CSV plotting status monitor (graphs of flow rate & temperature over time)"""
        if not self.current_status_log_path:
            return messagebox.showwarning(
                "No status log",
                "No status log file available yet. Start an experiment first."
            )
        if self.status_window is None or not self.status_window.winfo_exists():
            self.status_window = open_csv_status_monitor(
                self,
                self.current_status_log_path,
                self.instrument_types,
                update_interval_ms=60_000,  # 1 min
            )
        else:
            self.status_window.lift()
            self.status_window.focus_force()

    def _open_live_device_status(self) -> None:
        """Open text-based live instrument status monitor"""
        if not self.current_experiment_instruments:
            return messagebox.showwarning(
                "No instruments",
                "No active experiment with instruments. Start an experiment first."
            )
        if self.live_status_window is None or not self.live_status_window.winfo_exists():
            self.live_status_window = open_live_status_monitor(
                self.current_experiment_instruments,
                interval=5  # Update every 5 seconds
            )
        else:
            self.live_status_window.lift()
            self.live_status_window.focus_force()

    def _show_run_history(self) -> None:
        self._refresh_history_from_fs()
        try:
            self.history_listbox.focus_set()
        except Exception:
            pass

    # ────────────────────────── LOG PANEL
    def _build_log_panel(self) -> None:
        frame = ttk.LabelFrame(self, text="Log output")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        self.log_text = scrolledtext.ScrolledText(frame, state="disabled", wrap="word", height=8)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _append_log(self, text: str) -> None:
        def write():
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, text)
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")
        self.log_text.after(0, write)

    # ────────────────────────── RUN HISTORY
    def _build_history_panel(self) -> None:
        frame = ttk.LabelFrame(self, text="Run History")
        frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=6)

        left = ttk.Frame(frame)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ttk.Label(left, text="Previous runs (this session & output folder):") \
            .pack(anchor="w")

        self.history_listbox = tk.Listbox(left, height=5)
        self.history_listbox.pack(fill=tk.BOTH, expand=True, padx=(0, 4), pady=4)

        right = ttk.Frame(frame)
        right.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Button(right, text="Refresh from output dir", command=self._refresh_history_from_fs)\
            .pack(fill=tk.X, padx=4, pady=2)
        ttk.Button(right, text="Open selected folder", command=self._open_selected_history)\
            .pack(fill=tk.X, padx=4, pady=2)

    def _register_run(self, exp: GeneralExperimentMethod) -> None:
        info = {
            "experiment_dir": exp.experiment_subdir,
            "status_log": exp.status_log_filename,
            "log_csv": exp.log_filename,
        }
        self.run_history.append(info)

        label = os.path.basename(exp.experiment_subdir)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        display = f"{ts} – {label}"

        def _update():
            self.history_listbox.insert(tk.END, display)

        self.after(0, _update)

    def _refresh_history_from_fs(self) -> None:
        root = self.output_entry.get().strip() or os.getcwd()
        if not os.path.isdir(root):
            return

        self.history_listbox.delete(0, tk.END)
        self.run_history.clear()

        for date_dir in sorted(os.listdir(root)):
            full_date = os.path.join(root, date_dir)
            if not os.path.isdir(full_date):
                continue
            for sub in sorted(os.listdir(full_date)):
                exp_dir = os.path.join(full_date, sub)
                if not os.path.isdir(exp_dir):
                    continue
                status_logs = glob.glob(os.path.join(exp_dir, "*_Status_Log.csv"))
                main_logs = glob.glob(os.path.join(exp_dir, "*_AUTO_ZAHRT_Run.csv"))
                info = {
                    "experiment_dir": exp_dir,
                    "status_log": status_logs[0] if status_logs else "",
                    "log_csv": main_logs[0] if main_logs else "",
                }
                self.run_history.append(info)
                display = f"{date_dir} / {sub}"
                self.history_listbox.insert(tk.END, display)

    def _open_selected_history(self) -> None:
        idxs = self.history_listbox.curselection()
        if not idxs:
            return
        idx = idxs[0]
        if idx < 0 or idx >= len(self.run_history):
            return
        path = self.run_history[idx]["experiment_dir"]
        if not os.path.isdir(path):
            messagebox.showerror("Open error", f"Folder not found:\n{path}")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Open error", f"Could not open folder:\n{e}")

    # ────────────────────────── UV-VIS launcher
    def _open_uvvis_gui(self) -> None:
        try:
            root = Path(__file__).resolve().parents[1]
            gui_script = root / "UV_VIS_Detector" / "UV_VIS_platform_GUI.py"
            if not gui_script.exists():
                raise FileNotFoundError(f"{gui_script} not found")
            subprocess.Popen([sys.executable, str(gui_script)])
        except Exception as e:
            messagebox.showerror("Launch error", f"Could not launch UV-Vis GUI:\n{e}")


# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = AutoZahrtGUI()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    app.mainloop()
