import tkinter as tk
from tkinter import ttk
from config.settings import settings


class ParamsWidget:
    """生成参数控件 - 自动适配当前模型"""

    def __init__(self, parent, model_widget=None):
        self.parent = parent
        self.model_widget = model_widget
        self._create_widgets()
        self._apply_defaults()

    def _create_widgets(self):
        frame = ttk.LabelFrame(self.parent, text="⚙️ 生成参数", padding="10")
        frame.pack(fill=tk.X, pady=(0, 10))
        self.frame = frame

        # 步数/CFG/FPS
        row1 = ttk.Frame(frame)
        row1.pack(fill=tk.X, pady=2)
        self.steps = self._add_spin(row1, "步数:", 50, 10, 100, 5)
        self.cfg = self._add_spin(row1, "CFG:", 7.5, 1.0, 15.0, 0.5)
        self.fps = self._add_spin(row1, "FPS:", 8, 4, 15, 1)

        # 宽/高/帧数
        row2 = ttk.Frame(frame)
        row2.pack(fill=tk.X, pady=2)
        self.width = self._add_spin(row2, "宽度:", 576, 128, 768, 32)
        self.height = self._add_spin(row2, "高度:", 320, 128, 768, 32)
        self.frames = self._add_spin(row2, "帧数:", 30, 8, 50, 2)

        # 种子
        row3 = ttk.Frame(frame)
        row3.pack(fill=tk.X, pady=2)
        self.seed = self._add_spin(row3, "种子:", -1, -1, 999999, 1)

        ttk.Label(frame, text="💡 参数越高质量越好，耗时越长 | 种子 -1 随机", foreground="gray", font=("", 8)).pack(anchor=tk.W, pady=(5, 0))

    def _add_spin(self, parent, label, default, min_val, max_val, step):
        ttk.Label(parent, text=label).pack(side=tk.LEFT, padx=(0, 5))
        var = tk.DoubleVar(value=default) if isinstance(default, float) else tk.IntVar(value=default)
        spin = ttk.Spinbox(parent, from_=min_val, to=max_val, textvariable=var, width=6, increment=step)
        spin.pack(side=tk.LEFT, padx=(0, 15))
        return var

    def _apply_defaults(self):
        """应用当前模型的默认参数"""
        self.steps.set(settings.DEFAULT_NUM_INFERENCE_STEPS)
        self.cfg.set(settings.DEFAULT_GUIDANCE_SCALE)
        self.fps.set(settings.DEFAULT_FPS)
        self.width.set(settings.DEFAULT_WIDTH)
        self.height.set(settings.DEFAULT_HEIGHT)
        self.frames.set(settings.DEFAULT_NUM_FRAMES)

    def refresh_defaults(self):
        """刷新为当前模型默认值（模型切换时调用）"""
        self._apply_defaults()

    def get_params(self):
        return {
            "steps": int(self.steps.get()),
            "cfg": float(self.cfg.get()),
            "fps": int(self.fps.get()),
            "width": int(self.width.get()),
            "height": int(self.height.get()),
            "frames": int(self.frames.get()),
            "seed": int(self.seed.get()) if int(self.seed.get()) != -1 else None,
        }

    def get_frame(self):
        return self.frame