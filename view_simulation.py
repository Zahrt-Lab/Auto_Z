# TODO : Should delete this file in the future

"""
View the simulated experiment status in real-time
"""
import tkinter as tk
from utils.status import open_status_monitor

# Define instrument types for the simulated experiment
instrument_types = {
    "Pump_1": "VICI_M6_Pump",
    "Temperature_1": "Temperature"
}

# Create the GUI
root = tk.Tk()
root.withdraw()  # Hide the main window

# Open status monitor with simulated data
status_window = open_status_monitor(
    master=root,
    status_log_path="simulated_status_log.csv",
    instrument_types=instrument_types,
    update_interval_ms=5000,  # Update every 5 seconds
)

# Trigger initial plot
status_window.update_plot()

# Start auto-update
status_window.start_auto_update()

print("Status monitor opened. Close the window to exit.")

# Run the GUI
root.mainloop()
