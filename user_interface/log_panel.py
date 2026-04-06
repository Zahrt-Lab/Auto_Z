# log_panel.py
# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext, ttk


class LogPanel(ttk.Frame):
    """Scrolled text panel that displays experiment log output."""

    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent)
        self.app = app
        self._build()
        app.log_panel = self

    def _build(self) -> None:
        frame = ttk.LabelFrame(self, text="Log output")
        frame.pack(fill=tk.BOTH, expand=True)
        self.app.log_text = scrolledtext.ScrolledText(frame, state="disabled", wrap="word", height=10)
        self.app.log_text.pack(fill=tk.BOTH, expand=True)
