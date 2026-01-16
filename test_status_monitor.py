# TODO : Should delete this scriptin the future use

"""
Quick test script to view the status monitor with mock data
"""
import tkinter as tk
from utils.status import open_status_monitor

# Define instrument types for the mock data
instrument_types = {
    "Pump_1": "VICI_M6_Pump",
    "IsameticPump_1": "Isametic",
    "Temperature_1": "Temperature",
    "VICI-6Way_1": "Valve6Way",
    "GX-281_1": "GX281"
}

# Create the GUI
root = tk.Tk()
root.withdraw()  # Hide the main window

# Open status monitor with mock data
status_window = open_status_monitor(
    master=root,
    status_log_path="mock_status_log.csv",
    instrument_types=instrument_types,
    update_interval_ms=5000,  # Update every 5 seconds
)

# Trigger initial plot
status_window.update_plot()

# Run the GUI
root.mainloop()
