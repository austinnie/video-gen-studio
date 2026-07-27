import tkinter as tk
from tkinter import ttk


class ProgressWidget:
    """进度控件"""

    def __init__(self, parent):
        self.parent = parent
        self._create_widgets()

    def _create_widgets(self):
        frame = ttk.LabelFrame(self.parent, text="📊 进度", padding="10")
        frame.pack(fill=tk.X, pady=(0, 10))
        self.frame = frame

        self.var = tk.DoubleVar(value=0)
        self.bar = ttk.Progressbar(frame, variable=self.var, maximum=100)
        self.bar.pack(fill=tk.X)

        self.status_label = ttk.Label(frame, text="就绪", foreground="blue")
        self.status_label.pack(anchor=tk.W, pady=(5, 0))

    def update(self, value, message):
        self.var.set(value)
        self.status_label.config(text=message)

    def reset(self):
        self.var.set(0)
        self.status_label.config(text="就绪")

    def get_frame(self):
        return self.frame