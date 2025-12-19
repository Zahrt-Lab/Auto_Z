"""
Status Monitor GUI utilities for AUTO_ZAHRT
"""
import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Dict, List, Any


def group_for_instrument_type(instrument_type: str) -> str:
    """
    Return a display group name for the given instrument type.
    Used to organize instruments in the status monitor and map to action groups.
    """
    groups = {
        'GX281': 'LiquidHandler',
        'Ender3_Liquid_Handler': 'LiquidHandler',
        'VICI_M6_Pump': 'Pump',
        'Isametic': 'Pump',
        'PhdUltraPump': 'Pump',
        'Valve6Way': 'Valve',
        'Valve10Way': 'Valve',
        'Valve24Way': 'Valve',
        'Temperature': 'Temperature',
    }
    return groups.get(instrument_type, 'Other')


def open_status_monitor(instruments: Dict[str, Any], interval: int = 5):
    """
    Open a status monitor window that displays real-time status of all instruments.
    
    Args:
        instruments: Dictionary of {name: instrument_object}
        interval: Update interval in seconds
    """
    monitor_window = tk.Toplevel()
    monitor_window.title("AUTO_ZAHRT - Instrument Status Monitor")
    monitor_window.geometry("800x600")
    
    # Create main frame
    main_frame = ttk.Frame(monitor_window, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    # Title
    title_label = ttk.Label(main_frame, text="Instrument Status Monitor", 
                            font=('Arial', 14, 'bold'))
    title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
    
    # Create scrolled text widget for status display
    status_text = tk.Text(main_frame, height=30, width=90, wrap=tk.WORD)
    status_text.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    # Add scrollbar
    scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=status_text.yview)
    scrollbar.grid(row=1, column=2, sticky=(tk.N, tk.S))
    status_text['yscrollcommand'] = scrollbar.set
    
    # Control variables
    monitoring_active = {'active': True}
    
    def update_status():
        """Update the status display for all instruments."""
        while monitoring_active['active']:
            try:
                status_text.delete('1.0', tk.END)
                status_text.insert('1.0', f"Last Update: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                status_text.insert(tk.END, "=" * 80 + "\n\n")
                
                # Group instruments by type
                grouped = {}
                for name, instrument in instruments.items():
                    # Get instrument type from the name or class
                    inst_type = name.split('_')[0] if '_' in name else type(instrument).__name__
                    group = group_for_instrument_type(inst_type)
                    
                    if group not in grouped:
                        grouped[group] = []
                    grouped[group].append((name, instrument))
                
                # Display each group
                for group_name, group_instruments in sorted(grouped.items()):
                    status_text.insert(tk.END, f"📊 {group_name}\n", 'group_header')
                    status_text.insert(tk.END, "-" * 80 + "\n")
                    
                    for name, instrument in group_instruments:
                        # Try to get status from the instrument
                        try:
                            if hasattr(instrument, 'status') and callable(instrument.status):
                                status = instrument.status()
                            else:
                                status = "No status() method available"
                        except Exception as e:
                            status = f"Error getting status: {e}"
                        
                        status_text.insert(tk.END, f"  {name}: {status}\n")
                    
                    status_text.insert(tk.END, "\n")
                
                # Configure tag for group headers
                status_text.tag_config('group_header', font=('Arial', 11, 'bold'), 
                                      foreground='#2E86AB')
                
            except Exception as e:
                status_text.delete('1.0', tk.END)
                status_text.insert('1.0', f"Error updating status: {e}\n")
            
            time.sleep(interval)
    
    def on_close():
        """Handle window close event."""
        monitoring_active['active'] = False
        monitor_window.destroy()
    
    monitor_window.protocol("WM_DELETE_WINDOW", on_close)
    
    # Start monitoring thread
    monitor_thread = threading.Thread(target=update_status, daemon=True)
    monitor_thread.start()
    
    # Configure grid weights
    monitor_window.columnconfigure(0, weight=1)
    monitor_window.rowconfigure(0, weight=1)
    main_frame.columnconfigure(0, weight=1)
    main_frame.rowconfigure(1, weight=1)
    
    return monitor_window
