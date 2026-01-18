# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Ocean Optics UV-Vis GUI (Tkinter)

• Matches the look/feel of your sample Tkinter app, with added functions from your device class:
  - Device Info, Close Device
  - Save/Load Dark & Blank spectra (CSV+PNG)
  - Apply parameters after init (integration, scans, interval, targets)
  - Single Spectrum → Absorbance snapshot saver
  - Start/Stop Continuous with live plots

Dependencies:
    pip install matplotlib pandas numpy

Usage:
    Place this file where `AUTO_ZAHRT.UV_VIS_Detector.UV_VIS_platform` is importable
    python uv_vis_tk_gui.py
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path
import time
from typing import List

# Ensure TkAgg backend for interactive plotting in Tk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import numpy as np
import pandas as pd
from pandas.errors import EmptyDataError

# ------------------------------------------------------------------
#  🔁  IMPORT YOUR DEVICE CLASS (unchanged path as in your sample)
# ------------------------------------------------------------------
try:
    from AUTO_ZAHRT.UV_VIS_Detector.UV_VIS_platform_v2 import Ocean_Optics_UV_vis
except Exception as e:
    Ocean_Optics_UV_vis = None  # We'll error nicely on init


class UVVisApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ocean Optics UV-Vis (Tkinter)")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.device: Ocean_Optics_UV_vis | None = None
        self.polling = False
        self.time_data: List[float] = []
        self.abs_time: List[float] = []

        self._build_ui()
        self._build_plot()

    # ────────────────────────────────────────────────────────── UI
    def _build_ui(self):
        frm = ttk.Frame(self, padding=8)
        frm.pack(fill=tk.X)

        # Output directory
        ttk.Label(frm, text="Output Dir:").grid(row=0, column=0, sticky=tk.W)
        self.dir_var = tk.StringVar(value=str(Path.cwd()))
        ttk.Entry(frm, textvariable=self.dir_var, width=36).grid(row=0, column=1, padx=4)
        ttk.Button(frm, text="Browse…", command=self._choose_dir).grid(row=0, column=2, padx=(0,8))

        # Scans
        ttk.Label(frm, text="Scans:").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.scans_var = tk.IntVar(value=10)
        ttk.Spinbox(frm, from_=1, to=10000, textvariable=self.scans_var, width=8).grid(row=1, column=1, sticky=tk.W)

        # Integration time
        ttk.Label(frm, text="Integration (µs):").grid(row=1, column=2, sticky=tk.W)
        self.int_var = tk.IntVar(value=100000)
        ttk.Spinbox(frm, from_=1, to=9_999_999, increment=1000, textvariable=self.int_var, width=10).grid(row=1, column=3, sticky=tk.W)

        # Target wavelengths
        ttk.Label(frm, text="Targets (nm):").grid(row=2, column=0, sticky=tk.W)
        self.wls_var = tk.StringVar(value="409.0")
        ttk.Entry(frm, textvariable=self.wls_var, width=36).grid(row=2, column=1, columnspan=2, sticky=tk.W)
        ttk.Label(frm, text="comma-separated").grid(row=2, column=3, sticky=tk.W)

        # Interval
        ttk.Label(frm, text="Interval (s):").grid(row=3, column=0, sticky=tk.W, pady=4)
        self.interval_var = tk.DoubleVar(value=20.0)
        ttk.Spinbox(frm, from_=0.1, to=3600.0, increment=0.1, textvariable=self.interval_var, width=8).grid(row=3, column=1, sticky=tk.W)
        ttk.Label(frm, text="seconds").grid(row=3, column=2, sticky=tk.W)

        # Name
        ttk.Label(frm, text="Name:").grid(row=4, column=0, sticky=tk.W, pady=4)
        self.name_var = tk.StringVar(value="UV_run")
        ttk.Entry(frm, textvariable=self.name_var, width=36).grid(row=4, column=1, columnspan=2, sticky=tk.W)

        # Buttons row 1 (like your sample)
        btns = ttk.Frame(self, padding=(0, 8))
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Initialize", command=self._on_init).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Record Spectrum", command=self._on_record).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Record Blank", command=self._on_blank).pack(side=tk.LEFT, padx=4)
        ttk.Button(btns, text="Record Dark", command=self._on_dark).pack(side=tk.LEFT, padx=4)
        self.cont_btn = ttk.Button(btns, text="Start Continuous", command=self._toggle_cont)
        self.cont_btn.pack(side=tk.LEFT, padx=4)

        # Buttons row 2 (added functions)
        extras = ttk.Frame(self, padding=(0, 0))
        extras.pack(fill=tk.X)
        ttk.Button(extras, text="Device Info", command=self._on_info).pack(side=tk.LEFT, padx=4)
        ttk.Button(extras, text="Close Device", command=self._on_close_device).pack(side=tk.LEFT, padx=4)
        ttk.Button(extras, text="Save Dark…", command=self._save_dark).pack(side=tk.LEFT, padx=4)
        ttk.Button(extras, text="Load Dark…", command=self._load_dark).pack(side=tk.LEFT, padx=4)
        ttk.Button(extras, text="Save Blank…", command=self._save_blank).pack(side=tk.LEFT, padx=4)
        ttk.Button(extras, text="Load Blank…", command=self._load_blank).pack(side=tk.LEFT, padx=4)
        ttk.Button(extras, text="Apply Params", command=self._apply_params).pack(side=tk.LEFT, padx=4)
        ttk.Button(extras, text="Save Absorbance Snapshot", command=self._save_absorbance_snapshot).pack(side=tk.LEFT, padx=4)

    # ────────────────────────────────────────────────────── plot
    def _build_plot(self):
        # One row, two columns (spectrum, timecourse)
        self.fig, (self.ax_spec, self.ax_time) = plt.subplots(1, 2, figsize=(12, 5))
        # Spectrum plot
        self.ax_spec.set_xlabel("Wavelength (nm)")
        self.ax_spec.set_ylabel("Absorbance")
        self.ax_spec.grid(True)
        # Time-course plot
        self.ax_time.set_xlabel("Time (s)")
        self.ax_time.set_ylabel("Absorbance @ target")
        self.ax_time.grid(True)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.fig.tight_layout()

    # ─────────────────────────────────────────────────── helpers
    def _choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.dir_var.get(), title="Select Output Folder")
        if d:
            self.dir_var.set(d)

    def _check_dev(self) -> bool:
        if self.device is None:
            messagebox.showwarning("Not initialized", "Please initialize the spectrometer first.")
            return False
        return True

    def _parse_targets(self) -> List[float]:
        try:
            return [float(x) for x in self.wls_var.get().replace(";", ",").split(",") if x.strip()]
        except ValueError:
            messagebox.showerror("Error", "Invalid target wavelengths.")
            raise

    # ───────────────────────────────────────── device actions
    def _on_init(self):
        if Ocean_Optics_UV_vis is None:
            return messagebox.showerror("Import error", "Could not import Ocean_Optics_UV_vis from AUTO_ZAHRT.UV_VIS_Detector.UV_VIS_platform")
        try:
            targets = self._parse_targets()
        except Exception:
            return
        try:
            outdir = Path(self.dir_var.get()).expanduser()
            outdir.mkdir(parents=True, exist_ok=True)
            fname = f"{self.name_var.get()}.csv"
            self.device = Ocean_Optics_UV_vis(
                output_dir=str(outdir),
                num_scans=self.scans_var.get(),
                integration_time=self.int_var.get(),
                target_wavelengths=targets,
                save_file_path=fname,
                measurement_interval=self.interval_var.get(),
            )
            self.device.initialize_Ocean_Optics_UV_VIS()
            self.device.set_measurement_interval(self.interval_var.get())
            messagebox.showinfo("Success", "Spectrometer initialized.")
        except Exception as e:
            messagebox.showerror("Initialization failed", str(e))

    def _on_info(self):
        if not self._check_dev():
            return
        try:
            self.device.retrieve_Ocean_Optics_Model()
            messagebox.showinfo("Device Info", f"Serial: {self.device.serial} Model: {self.device.model}")
        except Exception as e:
            messagebox.showerror("Device Info", str(e))

    def _on_close_device(self):
        if not self._check_dev():
            return
        try:
            self.device.close_device()
            messagebox.showinfo("Closed", "Device closed successfully.")
        except Exception as e:
            messagebox.showerror("Close Device", str(e))

    def _apply_params(self):
        if not self._check_dev():
            return
        try:
            self.device.set_number_of_scans(int(self.scans_var.get()))
            self.device.integration_time = int(self.int_var.get())
            self.device.set_integration_time()
            self.device.set_measurement_interval(float(self.interval_var.get()))
            self.device.set_target_wavelength(self._parse_targets())
            messagebox.showinfo("Applied", "Parameters applied to device.")
        except Exception as e:
            messagebox.showerror("Apply Params", str(e))

    def _on_record(self):
        if not self._check_dev():
            return
        try:
            self.device.recording_UV_VIS_Spectrum()
            self.device.calculate_absorbance_spectrum()
            self._update_spec(self.device.wavelengths, self.device.absorbance_spectrum)
        except Exception as e:
            messagebox.showerror("Record Spectrum", str(e))

    def _on_blank(self):
        if not self._check_dev():
            return
        try:
            self.device.generate_and_record_blank_spectrum()
            self._update_spec(self.device.wavelengths, self.device.blank_spectrum)
        except Exception as e:
            messagebox.showerror("Record Blank", str(e))

    def _on_dark(self):
        if not self._check_dev():
            return
        try:
            self.device.generate_and_record_dark_spectrum()
            wl = self.device.wavelengths
            self._update_spec(wl, self.device.dark_spectrum)
        except Exception as e:
            messagebox.showerror("Record Dark", str(e))

    # ───────────────────────────────────────── save/load helpers
    def _save_dark(self):
        if not self._check_dev():
            return
        directory = filedialog.askdirectory(initialdir=self.dir_var.get(), title="Select output directory for dark")
        if not directory:
            return
        base = tk.simpledialog.askstring("Filename base", "Base name:", initialvalue="dark_spectrum")
        if not base:
            return
        try:
            self.device.save_dark_spectrum(directory, filename=base)
            messagebox.showinfo("Saved", f"Dark spectrum saved to {directory}")
        except Exception as e:
            messagebox.showerror("Save Dark", str(e))

    def _load_dark(self):
        if not self._check_dev():
            return
        path = filedialog.askopenfilename(initialdir=self.dir_var.get(), title="Load dark spectrum CSV", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            self.device.load_dark_spectrum_from_csv(path, apply_to_device=True)
            messagebox.showinfo("Loaded", f"Loaded dark: {Path(path).name}")
        except Exception as e:
            messagebox.showerror("Load Dark", str(e))

    def _save_blank(self):
        if not self._check_dev():
            return
        directory = filedialog.askdirectory(initialdir=self.dir_var.get(), title="Select output directory for blank")
        if not directory:
            return
        base = tk.simpledialog.askstring("Filename base", "Base name:", initialvalue="blank_spectrum")
        if not base:
            return
        try:
            self.device.save_blank_spectrum(directory, filename=base)
            messagebox.showinfo("Saved", f"Blank spectrum saved to {directory}")
        except Exception as e:
            messagebox.showerror("Save Blank", str(e))

    def _load_blank(self):
        if not self._check_dev():
            return
        path = filedialog.askopenfilename(initialdir=self.dir_var.get(), title="Load blank spectrum CSV", filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        try:
            self.device.load_blank_spectrum_from_csv(path)
            messagebox.showinfo("Loaded", f"Loaded blank: {Path(path).name}")
        except Exception as e:
            messagebox.showerror("Load Blank", str(e))

    def _save_absorbance_snapshot(self):
        if not self._check_dev():
            return
        try:
            # Ensure current absorbance exists; if not, measure once
            if getattr(self.device, "absorbance_spectrum", None) is None:
                self.device.recording_UV_VIS_Spectrum()
                self.device.calculate_absorbance_spectrum()
            csv_path, png_path = self.device.save_and_plot(Path(self.device.output_dir))
            messagebox.showinfo("Saved", f"Saved snapshot: {Path(csv_path).name} {Path(png_path).name}")
        except Exception as e:
            messagebox.showerror("Save Absorbance", str(e))

    # ───────────────────────────────────────── continuous mode
    def _toggle_cont(self):
        if not self._check_dev():
            return
        if not self.polling:
            # reset time series
            self.time_data.clear()
            self.abs_time.clear()
            self.device.set_measurement_interval(self.interval_var.get())
            # ensure CSV name uses current run name
            self.device.save_file_path = Path(self.device.output_dir) / f"{self.name_var.get()}.csv"
            self.device.start_continuous(name=self.name_var.get())
            self.polling = True
            self.cont_btn.config(text="Stop Continuous")
            self.after(int(self.device.measurement_interval * 1000), self._live_update)
        else:
            self.device.stop_continuous()
            self.polling = False
            self.cont_btn.config(text="Start Continuous")

    def _live_update(self):
        """Poll and update both plots while in continuous mode."""
        if not self.polling:
            return
        try:
            # Update spectrum if available
            if self.device.wavelengths is not None and self.device.absorbance_spectrum is not None:
                self._update_spec(self.device.wavelengths, self.device.absorbance_spectrum)
                # Append time and first-target absorbance
                t = (self.time_data[-1] + self.device.measurement_interval) if self.time_data else 0.0
                vals = self.device.get_absorbance_at_target_wavelengths()
                a0 = float(vals[0] if isinstance(vals, (list, tuple, np.ndarray)) else vals)
                self.time_data.append(t)
                self.abs_time.append(a0)
                self._update_time(self.time_data, self.abs_time)
        finally:
            self.after(int(self.device.measurement_interval * 1000), self._live_update)

    # ──────────────────────────────────────────── helper plot methods
    def _update_spec(self, x, y):
        self.ax_spec.clear()
        self.ax_spec.plot(x, y)
        self.ax_spec.set_xlabel("Wavelength (nm)")
        self.ax_spec.set_ylabel("Absorbance")
        self.ax_spec.grid(True)
        self.fig.tight_layout()
        self.canvas.draw()

    def _update_time(self, t, y):
        self.ax_time.clear()
        self.ax_time.plot(t, y)
        label_nm = None
        try:
            if self.device and self.device.target_wavelengths:
                label_nm = self.device.target_wavelengths[0]
        except Exception:
            pass
        self.ax_time.set_xlabel("Time (s)")
        self.ax_time.set_ylabel(f"Absorbance @ {label_nm if label_nm is not None else 'target'} nm")
        self.ax_time.grid(True)
        self.fig.tight_layout()
        self.canvas.draw()

    # ───────────────────────────────────────── window close
    def _on_close(self):
        try:
            if self.polling and self.device is not None:
                self.device.stop_continuous()
        except Exception:
            pass
        try:
            if self.device is not None:
                self.device.close_device()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    app = UVVisApp()
    app.geometry("1000x680")
    app.mainloop()