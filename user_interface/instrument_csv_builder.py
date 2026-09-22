# instrument_csv_builder.py
# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

from __future__ import annotations

import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional, Callable

from methods.registry_loader import get_all_types, get_default_rows

# ──────────────────────────────────────────────────────────────────────────────
# Constants

COLUMNS = ("InstrumentType", "DeviceNumber", "Name", "COMPort", "OtherParams")

INSTRUMENT_CHOICES = get_all_types()
DEFAULT_ROWS = get_default_rows()


# ──────────────────────────────────────────────────────────────────────────────
# Instrument CSV Builder dialog

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
                self.tree.column(c, anchor="center", width=180, stretch=False)
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
            sv = tk.StringVar(value=old_val if str(old_val).isdigit() else "1")
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
            # COMPort may be blank for OceanOptics_UVVis if it's USB auto-detect; allow it
            if itype != "OceanOptics_UVVis" and com.strip() == "":
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
        InstrumentCSVBuilder(root, on_save=on_save)
        root.mainloop()
    else:
        InstrumentCSVBuilder(master, on_save=on_save)
