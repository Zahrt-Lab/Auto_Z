# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Andrew Zahrt
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
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
