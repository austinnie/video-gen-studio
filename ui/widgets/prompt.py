import tkinter as tk
from tkinter import ttk
from config.settings import settings


class PromptWidget:
    """提示词控件"""

    def __init__(self, parent):
        self.parent = parent
        self._create_widgets()

    def _create_widgets(self):
        frame = ttk.LabelFrame(self.parent, text="📝 提示词", padding="10")
        frame.pack(fill=tk.X, pady=(0, 10))
        self.frame = frame

        ttk.Label(frame, text="正面提示词:").pack(anchor=tk.W)
        self.prompt_text = tk.Text(frame, height=4, wrap=tk.WORD, font=("微软雅黑", 10))
        self.prompt_text.pack(fill=tk.X, pady=(5, 10))
        self.prompt_text.insert("1.0", settings.DEFAULT_PROMPT)

        ttk.Label(frame, text="负面提示词:").pack(anchor=tk.W)
        self.neg_text = tk.Text(frame, height=2, wrap=tk.WORD, font=("微软雅黑", 10))
        self.neg_text.pack(fill=tk.X, pady=(5, 0))
        self.neg_text.insert("1.0", settings.DEFAULT_NEGATIVE_PROMPT)

    def get_prompt(self):
        return self.prompt_text.get("1.0", tk.END).strip()

    def get_negative(self):
        return self.neg_text.get("1.0", tk.END).strip()

    def set_prompt(self, text):
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert("1.0", text)

    def get_frame(self):
        return self.frame

    def set_negative(self, text):
        """设置负面提示词"""
        self.neg_text.delete("1.0", tk.END)
        self.neg_text.insert("1.0", text)        