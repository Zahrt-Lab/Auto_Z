"""
Quick viewer for simulated UV data.
Opens the UV plot GUI with the simulated data file.
"""

import tkinter as tk
from pathlib import Path
import sys

# Add parent directory to path to import uv_plot_gui
sys.path.insert(0, str(Path(__file__).parent))

from uv_detectors.uv_plot_gui import open_uv_plot_monitor

if __name__ == "__main__":
    csv_file = Path("simulated_uv_data.csv")
    
    if not csv_file.exists():
        print(f"Error: {csv_file} not found.")
        print("Run simulate_uv_experiment.py first to generate test data.")
        sys.exit(1)
    
    root = tk.Tk()
    root.withdraw()
    
    monitor = open_uv_plot_monitor(root, csv_file, update_interval_ms=5000)
    
    root.mainloop()
