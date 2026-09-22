# methods_gui.py
# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------
from __future__ import annotations

# Force the non-interactive Agg backend before any other import can initialize matplotlib.
# utils/status.py imports FigureCanvasTkAgg (TkAgg backend), which can win the backend
# race if it runs first, causing plt.figure()/plt.close() in background experiment threads
# to create and destroy Tk objects off the main thread → fatal Tcl_AsyncDelete crash.
import matplotlib
matplotlib.use("Agg")

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Optional, Dict, Any

# Add project root to path for imports
try:
    project_root = Path(__file__).parent.parent.resolve()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
except Exception:
    pass

from user_interface.file_selector_panel import FileSelectorPanel
from user_interface.command_builder_panel import CommandBuilderPanel
from user_interface.command_table_panel import CommandTablePanel
from user_interface.schedule_run_panel import ScheduleRunPanel
from user_interface.control_bar_panel import ControlBarPanel
from user_interface.log_panel import LogPanel


class AutoZahrtGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AUTO_Z – Scheduler & Runner")
        self.geometry("1100x860")

        # ── Shared data state ──────────────────────────────────────────────
        self.commands: list[dict[str, str | float]] = []
        self.param_entries: dict[str, ttk.Entry] = {}
        self.generated_csv_path: str | None = None

        self.instrument_types: Dict[str, str] = {}
        self.components: list[str] = []
        self._updating_component: bool = False

        self.current_status_log_path: Optional[str] = None
        self.current_instrument_control_file_path: str = "instrument_control.txt"
        self.current_dh2000_control_file_path: str = "dh2000_light_source_control.txt"
        self.current_experiment_instruments: Optional[Dict[str, Any]] = None

        self.status_window = None
        self.live_status_window = None

        # ── Widget placeholders (panels populate these) ────────────────────
        self.config_entry: Optional[ttk.Entry] = None
        self.output_entry: Optional[ttk.Entry] = None
        self.status_interval_entry: Optional[ttk.Entry] = None
        self.instrument_control_entry: Optional[ttk.Entry] = None
        self.dh2000_control_entry: Optional[ttk.Entry] = None
        self.comp_var: Optional[tk.StringVar] = None
        self.comp_cb: Optional[ttk.Combobox] = None
        self.act_var: Optional[tk.StringVar] = None
        self.act_cb: Optional[ttk.Combobox] = None
        self.param_frame: Optional[ttk.Frame] = None
        self.delay_entry: Optional[ttk.Entry] = None
        self.notes_entry: Optional[ttk.Entry] = None
        self.tree: Optional[ttk.Treeview] = None
        self.log_text = None
        self.datetime_entry: Optional[ttk.Entry] = None
        self.emergency_button = None

        # ── Panel references (set by each panel's __init__) ────────────────
        self.file_selector_panel: Optional[FileSelectorPanel] = None
        self.command_builder_panel: Optional[CommandBuilderPanel] = None
        self.command_table_panel: Optional[CommandTablePanel] = None
        self.schedule_run_panel: Optional[ScheduleRunPanel] = None
        self.control_bar_panel: Optional[ControlBarPanel] = None
        self.log_panel: Optional[LogPanel] = None

        # ── Build UI ───────────────────────────────────────────────────────
        file_sel = FileSelectorPanel(self, app=self)
        file_sel.pack(fill=tk.X, padx=10, pady=6)

        cmd_builder = CommandBuilderPanel(self, app=self)
        cmd_builder.pack(fill=tk.X, padx=10, pady=6)

        cmd_table = CommandTablePanel(self, app=self)
        cmd_table.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

        sched = ScheduleRunPanel(self, app=self)
        sched.pack(fill=tk.X, padx=10, pady=6)

        ctrl = ControlBarPanel(self, app=self)
        ctrl.pack(fill=tk.X, padx=10, pady=(4, 0))

        log = LogPanel(self, app=self)
        log.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)

    # ────────────────────────── LOG (called from background thread)
    def _append_log(self, text: str) -> None:
        def write():
            self.log_text.configure(state="normal")
            self.log_text.insert(tk.END, text)
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")
        self.log_text.after(0, write)

def main():
    """Main entry point for the AUTO_ZAHRT GUI application."""
    # TODO: DELETE the try/except block below — ttk.Style() before AutoZahrtGUI() creates
    # an implicit Tk root, giving a phantom second window. Move theme_use into
    # AutoZahrtGUI.__init__ after super().__init__() instead.
    #try:
    #    ttk.Style().theme_use("clam")
    #except tk.TclError:
    #    pass
    app = AutoZahrtGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
