#!/usr/bin/env python
"""
Simple launcher for AUTO_ZAHRT GUI
Automatically sets up the Python path and launches the GUI
"""
import sys
from pathlib import Path

# Add project root to Python path so imports work
project_root = Path(__file__).parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now import and run the GUI
from methods.methods_gui import AutoZahrtGUI
import tkinter as tk
from tkinter import ttk

if __name__ == "__main__":
    app = AutoZahrtGUI()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    app.mainloop()
