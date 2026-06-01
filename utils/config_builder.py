# ------------------------------------------------------------------------------
# Instrument Config Builder GUI for AUTO_ZAHRT (aligned columns)
# ------------------------------------------------------------------------------
# Requirements:
#   pip install pyserial
# ------------------------------------------------------------------------------

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import csv

try:
    import serial.tools.list_ports as list_ports
except ImportError:
    list_ports = None


# Instrument types recognized by your GeneralExperimentMethod.initialize_instruments()
INSTRUMENT_TYPES = [
    "GX281",
    "Ender3_Liquid_Handler",
    "VICI_M6_Pump",
    "Valve6Way",
    "Valve10Way",
    "Valve24Way",
    "Temperature",
    # Future:
    # "HarvardPump",
    # "Isametic",
]


class InstrumentRow:
    """
    Represents one editable row in the table.
    Widgets are placed directly into the shared `rows_frame` to keep columns aligned.
    """
    def __init__(self, parent: ttk.Frame, row_index: int, available_ports: list[str], prefill_port: str = "", description: str = "") -> None:
        self.parent: ttk.Frame = parent
        self.row_index: int = row_index

        # Tk variables
        self.com_var = tk.StringVar(value=prefill_port)
        self.type_var = tk.StringVar()
        self.device_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.other_var = tk.StringVar()

        # Widgets
        self.idx_label = ttk.Label(parent, text=str(row_index))

        self.com_cb = ttk.Combobox(
            parent,
            textvariable=self.com_var,
            values=available_ports,
            width=12,
            state="readonly" if available_ports else "normal"
        )

        self.desc_label = ttk.Label(parent, text=description, width=40, anchor="w")

        self.type_cb = ttk.Combobox(
            parent,
            textvariable=self.type_var,
            values=INSTRUMENT_TYPES,
            width=18,
            state="readonly",
        )

        self.device_entry = ttk.Entry(parent, textvariable=self.device_var, width=8)
        self.name_entry = ttk.Entry(parent, textvariable=self.name_var, width=18)
        self.other_entry = ttk.Entry(parent, textvariable=self.other_var, width=30)

    def grid(self):
        """Grid this row at its current row_index."""
        r = self.row_index
        self.idx_label.grid(row=r, column=0, padx=2, pady=2, sticky="w")
        self.com_cb.grid(row=r, column=1, padx=2, pady=2, sticky="ew")
        self.desc_label.grid(row=r, column=2, padx=2, pady=2, sticky="ew")
        self.type_cb.grid(row=r, column=3, padx=2, pady=2, sticky="ew")
        self.device_entry.grid(row=r, column=4, padx=2, pady=2, sticky="ew")
        self.name_entry.grid(row=r, column=5, padx=2, pady=2, sticky="ew")
        self.other_entry.grid(row=r, column=6, padx=2, pady=2, sticky="ew")

    def destroy(self):
        """Destroy this row's widgets."""
        self.idx_label.destroy()
        self.com_cb.destroy()
        self.desc_label.destroy()
        self.type_cb.destroy()
        self.device_entry.destroy()
        self.name_entry.destroy()
        self.other_entry.destroy()

    def set_row_index(self, new_index):
        """Update row index and re-grid."""
        self.row_index = new_index
        self.grid()


class ConfigBuilderGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Instrument Config Builder - AUTO_ZAHRT")
        self.geometry("1200x600")

        self.available_ports: list[str] = []
        self.port_descriptions: dict[str, str] = {}
        self.rows: list[InstrumentRow] = []

        self._build_widgets()
        self.scan_ports()

    # ----------------- UI setup -----------------

    def _build_widgets(self):
        # Top control bar
        top_frame = ttk.Frame(self)
        top_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        ttk.Button(top_frame, text="Scan COM Ports", command=self.scan_ports).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="Add Empty Row", command=self.add_empty_row).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="Load Config CSV", command=self.load_config).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="Save Config CSV", command=self.save_config).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="Quit", command=self.destroy).pack(side=tk.RIGHT, padx=2)

        # Scrollable container (header + rows are in same frame to keep columns aligned)
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(container)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.rows_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")

        self.rows_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)  # Windows / Linux
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)    # macOS up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)    # macOS down

        # Build header row in the same frame as data rows (row 0)
        self._build_header()

        # Configure column weights for the shared frame
        self.rows_frame.columnconfigure(0, weight=0)  # index
        self.rows_frame.columnconfigure(1, weight=0)  # COM
        self.rows_frame.columnconfigure(2, weight=2)  # description
        self.rows_frame.columnconfigure(3, weight=1)  # type
        self.rows_frame.columnconfigure(4, weight=0)  # device #
        self.rows_frame.columnconfigure(5, weight=1)  # name
        self.rows_frame.columnconfigure(6, weight=2)  # other params

    def _build_header(self):
        headers = [
            "#",
            "COM Port",
            "Description",
            "Instrument Type",
            "Device #",
            "Name",
            "Other Params",
        ]
        for col, text in enumerate(headers):
            lbl = ttk.Label(self.rows_frame, text=text, font=("TkDefaultFont", 9, "bold"))
            lbl.grid(row=0, column=col, padx=2, pady=(0, 4), sticky="w")

    def _on_mousewheel(self, event):
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")

    # ----------------- Row management -----------------

    def clear_rows(self):
        for r in self.rows:
            r.destroy()
        self.rows = []

    def add_row(self, prefill_port="", description=""):
        """
        Add a new row. Data rows start at row index 1 (header is row 0),
        so we store a 1-based row_index for the grid.
        """
        row_index = len(self.rows) + 1  # header is 0
        row = InstrumentRow(
            parent=self.rows_frame,
            row_index=row_index,
            available_ports=self.available_ports,
            prefill_port=prefill_port,
            description=description,
        )
        self.rows.append(row)
        row.grid()

    def add_empty_row(self):
        self.add_row(prefill_port="", description="")

    def rebuild_row_indices(self):
        # Reassign row numbers & re-grid
        for i, r in enumerate(self.rows, start=1):
            r.idx_label.config(text=str(i))
            r.set_row_index(i)

    # ----------------- COM scanning -----------------

    def scan_ports(self):
        """Scan available COM ports with pyserial and create one row per port."""
        if list_ports is None:
            messagebox.showerror(
                "pyserial not found",
                "pyserial is required for COM port scanning.\n\nInstall with:\n    pip install pyserial"
            )
            return

        ports = list(list_ports.comports())
        self.available_ports = [p.device for p in ports]
        self.port_descriptions = {
            p.device: f"{p.description} ({p.hwid})" for p in ports
        }

        # Remove current data rows (keep header in row 0)
        self.clear_rows()

        if not self.available_ports:
            messagebox.showinfo("No Ports", "No COM ports detected. You can still add rows manually.")
        else:
            for port in self.available_ports:
                desc = self.port_descriptions.get(port, "")
                self.add_row(prefill_port=port, description=desc)

        self.rebuild_row_indices()

    # ----------------- Load / Save CSV -----------------

    def save_config(self):
        """Collect rows and save as CSV with columns expected by GeneralExperimentMethod."""
        if not self.rows:
            messagebox.showwarning("No Data", "There are no rows to save.")
            return

        filename = filedialog.asksaveasfilename(
            title="Save Instrument Config",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return

        try:
            with open(filename, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["InstrumentType", "DeviceNumber", "Name", "COMPort", "OtherParams"])

                for i, row in enumerate(self.rows, start=1):
                    inst_type = row.type_var.get().strip()
                    device_number = row.device_var.get().strip()
                    name = row.name_var.get().strip()
                    com_port = row.com_var.get().strip()
                    other_params = row.other_var.get().strip()

                    # Skip fully empty row
                    if not (inst_type or device_number or name or com_port or other_params):
                        continue

                    if not inst_type:
                        # Warn & skip if instrument type is missing
                        messagebox.showwarning(
                            "Missing Instrument Type",
                            f"Row {i} has no InstrumentType; it will be skipped."
                        )
                        continue

                    if not name:
                        suffix = device_number if device_number else str(i)
                        name = f"{inst_type}_{suffix}"

                    writer.writerow([
                        inst_type,
                        device_number,
                        name,
                        com_port,
                        other_params
                    ])

            messagebox.showinfo("Saved", f"Configuration saved to:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error Saving", f"Failed to save config:\n{e}")

    def load_config(self):
        """Load existing CSV and populate the table."""
        filename = filedialog.askopenfilename(
            title="Open Instrument Config CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return

        try:
            with open(filename, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                required = ["InstrumentType", "DeviceNumber", "Name", "COMPort", "OtherParams"]
                if not set(required).issubset(reader.fieldnames or []):
                    messagebox.showerror(
                        "Invalid Format",
                        "CSV is missing one or more required columns:\n"
                        "InstrumentType, DeviceNumber, Name, COMPort, OtherParams"
                    )
                    return

                self.clear_rows()

                for row_dict in reader:
                    inst_type = row_dict.get("InstrumentType", "").strip()
                    device_number = row_dict.get("DeviceNumber", "").strip()
                    name = row_dict.get("Name", "").strip()
                    com_port = row_dict.get("COMPort", "").strip()
                    other = row_dict.get("OtherParams", "").strip()

                    desc = self.port_descriptions.get(com_port, "")
                    self.add_row(prefill_port=com_port, description=desc)
                    r = self.rows[-1]

                    r.type_var.set(inst_type)
                    r.device_var.set(device_number)
                    r.name_var.set(name)
                    r.other_var.set(other)

                self.rebuild_row_indices()

            messagebox.showinfo("Loaded", f"Loaded config from:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error Loading", f"Failed to load config:\n{e}")


if __name__ == "__main__":
    app = ConfigBuilderGUI()
    app.mainloop()
