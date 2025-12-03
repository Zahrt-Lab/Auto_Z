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
import os
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
import sys
import subprocess
from typing import Optional, Callable

# If your project structure requires it, keeping this path tweak helps resolve AUTO_ZAHRT.*
try:
    sys.path.insert(0, str(Path.cwd().parent.parent))
except Exception:
    pass

# ── Experiment runner (required external; unchanged)
try:
    from AUTO_ZAHRT.Methods.General_Methods import GeneralExperimentMethod
except ModuleNotFoundError:
    messagebox.showerror("Import error", "Cannot import GeneralExperimentMethod.")
    raise

# ──────────────────────────────────────────────────────────────────────────────
# Embedded Instrument CSV Builder (no external import needed)

COLUMNS = ("InstrumentType", "DeviceNumber", "Name", "COMPort", "OtherParams")

INSTRUMENT_CHOICES = [
    "GX281",
    "Pump",
    "HarvardPump",
    "Valve6Way",
    "Valve10Way",
    "Valve24Way",
    "Temperature",
]

DEFAULT_ROWS = [
    ("GX281",       "1", "GX-281",      "COM2",  ""),
    ("Pump",        "1", "Pump",        "COM17", ""),
    ("HarvardPump", "1", "HarvardPump", "COM4", ""),
    ("Valve6Way",   "1", "VICI-6Way",   "COM7",  ""),
    ("Valve6Way",   "2", "VICI-6Way",   "COM11", ""),
    ("Valve24Way",  "1", "VICI-24Way",  "COM13", ""),
    ("Valve24Way",  "2", "VICI-24Way",  "COM14", ""),
    ("Temperature", "1", "Temperature", "COM12", ""),
]


class InstrumentCSVBuilder(tk.Toplevel):
    """Inline copy of instrument_csv_builder; opens as a modal Toplevel."""

    def __init__(self, master: tk.Misc | None, on_save: Optional[Callable[[str], None]] = None) -> None:
        super().__init__(master)
        self.title("Instrument CSV Builder")
        self.geometry("1000x600")
        self.minsize(760, 420)
        self.resizable(True, True)

        self._on_save = on_save
        self.last_path: Optional[str] = None

        # Container
        wrap = ttk.Frame(self)
        wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Toolbar
        toolbar = ttk.Frame(wrap)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(toolbar, text="Open CSV…", command=self._open_csv).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text="Save as CSV…", command=self._save_csv).pack(side=tk.LEFT)
        ttk.Separator(toolbar, orient="vertical").pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(toolbar, text="Add Row", command=self._add_row).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Duplicate Row", command=self._dup_row).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Delete Row(s)", command=self._del_row).pack(side=tk.LEFT)

        ttk.Button(toolbar, text="Close", command=self.destroy).pack(side=tk.RIGHT)

        # Tree (table)
        self.tree = ttk.Treeview(wrap, columns=COLUMNS, show="headings", height=16)
        for c in COLUMNS:
            self.tree.heading(c, text=c)
            if c in ("OtherParams", "Name"):
                self.tree.column(c, anchor="w", width=260, stretch=True)
            elif c == "InstrumentType":
                self.tree.column(c, anchor="center", width=160, stretch=False)
            elif c == "COMPort":
                self.tree.column(c, anchor="center", width=120, stretch=False)
            else:  # DeviceNumber
                self.tree.column(c, anchor="center", width=120, stretch=False)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Populate defaults
        for row in DEFAULT_ROWS:
            self.tree.insert("", tk.END, values=row)

        # Hints + status
        ttk.Label(
            wrap,
            text="Tip: Double-click a cell to edit. InstrumentType is a dropdown; DeviceNumber is numeric.",
        ).pack(fill=tk.X, pady=(8, 4))
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status).pack(fill=tk.X, padx=10, pady=(0, 8))

        # Editing bind
        self.tree.bind("<Double-1>", self._on_double_click)

        # Theme
        try:
            ttk.Style().theme_use("clam")
        except tk.TclError:
            pass

        # Modal-ish
        self.transient(master)
        self.grab_set()
        self.focus()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    # ─────────────────────────── helpers
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

    # ─────────────────────────── inline editing
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

        # Specialized editors
        if col_name == "InstrumentType":
            widget = ttk.Combobox(self.tree, values=INSTRUMENT_CHOICES, state="readonly")
            widget.place(x=x, y=y, width=w, height=h)
            widget.set(old_val if old_val in INSTRUMENT_CHOICES else INSTRUMENT_CHOICES[0])
            widget.focus_set()
            widget.bind("<<ComboboxSelected>>", lambda *_: finish(widget.get()))
            widget.bind("<Return>", lambda *_: finish(widget.get()))
            widget.bind("<Escape>", lambda *_: widget.destroy())

        elif col_name == "DeviceNumber":
            # Simple numeric spinbox
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

    # ─────────────────────────── CSV IO
    def _validate_rows(self, rows: list[tuple[str, str, str, str, str]]) -> bool:
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

    def _collect_rows(self) -> list[tuple[str, str, str, str, str]]:
        return [tuple(self.tree.item(iid, "values")) for iid in self.tree.get_children("")]  # type: ignore[return-value]

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
                # Clear
                for iid in self.tree.get_children(""):
                    self.tree.delete(iid)
                # Load
                for row in reader:
                    vals = tuple(row.get(c, "") for c in COLUMNS)
                    self.tree.insert("", tk.END, values=vals)
            self.last_path = path
            self.status.set(f"Loaded {path}")
        except Exception as e:
            messagebox.showerror("Open error", str(e))


def launch_instrument_csv_builder(master: tk.Misc | None = None, on_save: Optional[Callable[[str], None]] = None) -> None:
    """Built-in launcher; identical signature to the external helper."""
    if master is None:
        root = tk.Tk()
        root.withdraw()
        dlg = InstrumentCSVBuilder(root, on_save=on_save)
        root.update_idletasks()
        dlg.update_idletasks()
        dlg.deiconify()
        root.mainloop()
    else:
        InstrumentCSVBuilder(master, on_save=on_save)

# ──────────────────────────────────────────────────────────────────────────────
# AUTO_ZAHRT main GUI

COMPONENT_ACTIONS: dict[str, list[str]] = {
    "GX-281": ["set_bedlayout", "move_home", "move_z_height", "move_xy", "move_z"],
    "Pump": ["aspirating", "dispensing"],
    "HarvardPump": ["select_syringe", "infuse", "stop"],
    "VICI-6Way": ["go_to_position", "move_home"],
    "VICI-10Way": ["go_to_position", "move_home"],
    "VICI-24Way": ["go_to_position", "move_home"],
    "Temperature": ["set_temperature"],
    "SYNC": ["wait_for_pumps"],
}

PARAMETERS_MAPPING: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("GX-281", "set_bedlayout"):       [("bed", "Bed"), ("rack_layout", "Rack Layout")],
    ("GX-281", "move_z_height"):       [("height", "Height")],
    ("GX-281", "move_xy"):             [("bed", "Bed"), ("well", "Well")],
    ("GX-281", "move_z"):              [("bed", "Bed"), ("well", "Well")],
    ("Pump", "aspirating"):            [("flow_rate", "Flow Rate"), ("volume", "Volume"), ("pump_id", "Pump ID")],
    ("Pump", "dispensing"):            [("flow_rate", "Flow Rate"), ("volume", "Volume"), ("pump_id", "Pump ID")],
    ("HarvardPump", "select_syringe"): [("syringe", "Syringe mL"), ("pump_id", "Pump ID")],
    ("HarvardPump", "infuse"):         [("volume", "Volume"), ("rate", "Rate"), ("pump_id", "Pump ID")],
    ("HarvardPump", "stop"):           [("pump_id", "Pump ID")],
    ("VICI-6Way", "go_to_position"):   [("position", "Position"), ("valve_id", "Valve ID")],
    ("VICI-6Way", "move_home"):        [("valve_id", "Valve ID")],
    ("VICI-10Way", "go_to_position"):  [("position", "Position"), ("valve_id", "Valve ID")],
    ("VICI-10Way", "move_home"):       [("valve_id", "Valve ID")],
    ("VICI-24Way", "go_to_position"):  [("position", "Position"), ("valve_id", "Valve ID")],
    ("VICI-24Way", "move_home"):       [("valve_id", "Valve ID")],
    ("Temperature", "set_temperature"): [("temp", "Temperature"), ("temp_id", "Controller ID")],
}


class AutoZahrtGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AUTO_ZAHRT – Scheduler & Runner")
        self.geometry("900x720")

        self.commands: list[dict[str, str|float]] = []
        self.param_entries: dict[str, ttk.Entry] = {}
        self.generated_csv_path: str|None = None

        self._build_file_selector()
        self._build_command_entry()
        self._build_command_tree()
        self._build_schedule_section()
        self._build_log_panel()

    # ─────────────────────────────────── FILE SELECTION
    def _build_file_selector(self) -> None:
        frame = ttk.LabelFrame(self, text="Files & Output")
        frame.pack(fill=tk.X, padx=10, pady=6)

        ttk.Label(frame, text="Instrument Config CSV:") \
            .grid(row=0, column=0, sticky=tk.W)
        self.config_entry = ttk.Entry(frame, width=60)
        self.config_entry.grid(row=0, column=1, padx=6, pady=2)

        ttk.Button(frame, text="Browse…", command=self._browse_config) \
            .grid(row=0, column=2, padx=4)

        # Build… button opens the embedded builder and fills the path on save.
        ttk.Button(
            frame, text="Build…", command=self._open_instrument_builder, state="normal"
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

    def _browse_output(self) -> None:
        d = filedialog.askdirectory()
        if d:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, d)

    def _open_instrument_builder(self) -> None:
        """Open the instrument CSV builder and auto-fill the config path on save."""
        def _on_save(path: str) -> None:
            self.config_entry.delete(0, tk.END)
            self.config_entry.insert(0, path)
            try:
                self.lift()
                self.focus_force()
            except Exception:
                pass

        # Launch embedded builder as a modal-ish dialog attached to this window
        launch_instrument_csv_builder(master=self, on_save=_on_save)

    # ─────────────────────────────────── COMMAND BUILDER
    def _build_command_entry(self) -> None:
        frame = ttk.LabelFrame(self, text="Add Command")
        frame.pack(fill=tk.X, padx=10, pady=6)

        ttk.Label(frame, text="Component:")\
            .grid(row=0, column=0, sticky=tk.W)
        self.comp_var = tk.StringVar()
        self.comp_cb = ttk.Combobox(
            frame, textvariable=self.comp_var,
            state="readonly", width=20
        )
        self.comp_cb["values"] = sorted(COMPONENT_ACTIONS.keys())
        self.comp_cb.bind("<<ComboboxSelected>>", self._on_component_change)
        self.comp_cb.grid(row=0, column=1, padx=3)

        ttk.Label(frame, text="Action:")\
            .grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        self.act_var = tk.StringVar()
        self.act_cb = ttk.Combobox(
            frame, textvariable=self.act_var,
            state="readonly", width=20
        )
        self.act_cb.bind("<<ComboboxSelected>>", self._rebuild_param_fields)
        self.act_cb.grid(row=0, column=3, padx=3)

        self.param_frame = ttk.Frame(frame)
        self.param_frame.grid(row=1, column=0, columnspan=4, pady=(8,0), sticky=tk.W)

        ttk.Label(frame, text="Delay (s):")\
            .grid(row=2, column=0, sticky=tk.W)
        self.delay_entry = ttk.Entry(frame, width=10)
        self.delay_entry.insert(0, "0.5")
        self.delay_entry.grid(row=2, column=1, sticky=tk.W)

        ttk.Label(frame, text="Notes:")\
            .grid(row=3, column=0, sticky=tk.W)
        self.notes_entry = ttk.Entry(frame, width=60)
        self.notes_entry.grid(row=3, column=1, columnspan=3, pady=(0,6), sticky=tk.W)

        ttk.Button(frame, text="Add Command", command=self._add_command)\
            .grid(row=4, column=0, columnspan=4, pady=4)

    def _on_component_change(self, _=None) -> None:
        comp = self.comp_var.get()
        self.act_cb["values"] = COMPONENT_ACTIONS.get(comp, [])
        if self.act_cb["values"]:
            self.act_cb.current(0)
        self._rebuild_param_fields()

    def _rebuild_param_fields(self, _=None) -> None:
        for w in self.param_frame.winfo_children():
            w.destroy()
        self.param_entries.clear()
        comp, act = self.comp_var.get(), self.act_var.get()
        for row, (key, label) in enumerate(PARAMETERS_MAPPING.get((comp, act), [])):
            ttk.Label(self.param_frame, text=f"{label}:")\
                .grid(row=row, column=0, sticky=tk.W)
            ent = ttk.Entry(self.param_frame, width=12)
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
        params = ",".join(f"{k}={e.get().strip()}" for k, e in self.param_entries.items())
        if any(e.get().strip() == "" for e in self.param_entries.values()):
            return messagebox.showerror("Input error", "Fill all parameters")
        notes = self.notes_entry.get().strip()
        cmd = {"Component": comp, "Action": act, "Parameters": params, "delay": delay, "Notes": notes}
        self.commands.append(cmd)
        self.tree.insert("", tk.END, values=(comp, act, params, delay, notes))
        for w in self.param_frame.winfo_children():
            w.destroy()
        self.param_entries.clear()
        self.notes_entry.delete(0, tk.END)

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
            self.tree.insert("", tk.END, values=(cmd["Component"], cmd["Action"], cmd["Parameters"], d, cmd["Notes"]))
        self.generated_csv_path = path
        messagebox.showinfo("Loaded", f"Loaded commands from {path}")

    def _clear_commands(self) -> None:
        self.commands.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.generated_csv_path = None

    def _build_schedule_section(self) -> None:
        frame = ttk.LabelFrame(self, text="Schedule & Run")
        frame.pack(fill=tk.X, padx=10, pady=6)
        ttk.Label(frame, text="Run at (YYYY-MM-DD HH:MM:SS):")\
            .grid(row=0, column=0, sticky=tk.W)
        self.datetime_entry = ttk.Entry(frame, width=25)
        self.datetime_entry.grid(row=0, column=1, padx=6)
        ttk.Button(frame, text="Schedule experiment", command=self._schedule_run)\
            .grid(row=0, column=2, padx=6)
        ttk.Button(frame, text="Run now", command=self._run_now)\
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
            orig_log = exp.log_to_csv

            def patched(comp, act, params, output, notes=""):
                orig_log(comp, act, params, output, notes)
                self._append_log(f"[{comp}] {act} – {output} ({notes})\n")

            exp.log_to_csv = patched  # type: ignore
            exp.run_experiment()
            self._append_log("\nExperiment finished successfully.\n")
            messagebox.showinfo("Done", "Experiment finished")
        except Exception as e:
            self._append_log(f"\n[ERROR] {e}\n")
            messagebox.showerror("Error", str(e))

    def _build_log_panel(self) -> None:
        frame = ttk.LabelFrame(self, text="Log output")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        self.log_text = scrolledtext.ScrolledText(frame, state="disabled", wrap="word", height=12)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _append_log(self, text: str) -> None:
        def write():
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, text)
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")
        self.log_text.after(0, write)

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
