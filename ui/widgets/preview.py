import tkinter as tk
from tkinter import ttk
import os


class PreviewWidget:
    """视频预览控件"""

    def __init__(self, parent):
        self.parent = parent
        self._create_widgets()

    def _create_widgets(self):
        frame = ttk.LabelFrame(self.parent, text="🎬 视频预览", padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        self.frame = frame

        self.label = ttk.Label(frame, text="生成后将在这里显示视频预览", foreground="gray")
        self.label.pack(expand=True)

    def show_video(self, video_path):
        self.label.config(text=f"✅ 视频已保存\n📁 {os.path.basename(video_path)}")

    def clear(self):
        self.label.config(text="生成后将在这里显示视频预览")

    def get_frame(self):
        return self.frame