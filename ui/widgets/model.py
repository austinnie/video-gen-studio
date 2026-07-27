import tkinter as tk
from tkinter import ttk
from pathlib import Path

from config.settings import settings
from core.model_loader import model_loader


class ModelWidget:
    """模型选择控件 - 支持多模型"""

    def __init__(self, parent, status_callback):
        self.parent = parent
        self.status_callback = status_callback
        self._create_widgets()
        self._update_status()

    def _create_widgets(self):
        frame = ttk.LabelFrame(self.parent, text="🤖 模型选择", padding="10")
        frame.pack(fill=tk.X, pady=(0, 10))
        self.frame = frame

        row = ttk.Frame(frame)
        row.pack(fill=tk.X, pady=2)

        ttk.Label(row, text="模型:").pack(side=tk.LEFT, padx=(0, 8))

        # 模型下拉框 - 使用显示名称列表
        self.model_names = settings.get_model_names()
        default_name = f"{settings.current_model.name} ({settings.current_model.size})" if settings.current_model else self.model_names[0]

        self.var = tk.StringVar(value=default_name)
        self.combo = ttk.Combobox(
            row,
            textvariable=self.var,
            values=self.model_names,
            width=35,
            state="readonly"
        )
        self.combo.pack(side=tk.LEFT, padx=(0, 10))
        self.combo.bind('<<ComboboxSelected>>', self._on_change)

        # 状态标签
        self.status_label = ttk.Label(row, text="", foreground="gray")
        self.status_label.pack(side=tk.LEFT, padx=(0, 10))

        # 下载按钮
        self.download_btn = ttk.Button(row, text="📦 下载", command=self._download, width=8)
        self.download_btn.pack(side=tk.LEFT)

        # 信息行
        info_row = ttk.Frame(frame)
        info_row.pack(fill=tk.X, pady=2)
        self.info_label = ttk.Label(info_row, text="", foreground="gray", font=("", 8))
        self.info_label.pack(anchor=tk.W)

        # 更新信息
        self._update_info()

    def _get_current_choice(self) -> str:
        """获取当前选中的模型标识"""
        display = self.var.get()
        choice = settings.get_choice_by_display(display)
        return choice or settings.AVAILABLE_MODELS[0].choice

    def _update_info(self):
        """更新模型信息"""
        choice = self._get_current_choice()
        model = settings.get_model_by_choice(choice)
        if model:
            self.info_label.config(text=model.description)

    def _update_status(self):
        """更新模型状态"""
        choice = self._get_current_choice()
        model = settings.get_model_by_choice(choice)
        if not model:
            return

        path = Path(settings.BASE_DIR) / "models" / model.local_dir
        if path.exists():
            # 检查是否有模型文件
            has_model = any(str(f).endswith(('.safetensors', '.bin', '.ckpt')) for f in path.rglob('*') if f.is_file())
            if has_model:
                self.status_label.config(text="✅ 已就绪", foreground="green")
                return
        self.status_label.config(text="❌ 未下载", foreground="red")

    def _on_change(self, event):
        """模型切换"""
        choice = self._get_current_choice()
        model = settings.get_model_by_choice(choice)
        if not model:
            return

        # 更新 settings
        settings.MODEL_CHOICE = choice

        # 卸载旧模型
        if model_loader.is_loaded():
            model_loader.unload_model()

        self._update_status()
        self._update_info()

        # 通知父组件更新参数默认值
        if self.status_callback:
            self.status_callback(f"已切换到: {model.name}")

    def _download(self):
        """下载当前选中的模型"""
        import threading
        import subprocess
        import sys

        choice = self._get_current_choice()
        model = settings.get_model_by_choice(choice)

        if not model:
            return

        if not tk.messagebox.askyesno("确认", f"确定要下载 {model.name} ({model.size}) 吗？\n\n可能需要较长时间，请耐心等待。"):
            return

        self.download_btn.config(state=tk.DISABLED)
        self.status_label.config(text="📦 下载中...", foreground="orange")

        def run():
            result = subprocess.run(
                [sys.executable, "scripts/download_model.py", "--model", choice],
                capture_output=True,
                text=True
            )
            self.parent.after(0, self._on_done, result.returncode == 0)

        threading.Thread(target=run, daemon=True).start()

    def _on_done(self, success):
        self.download_btn.config(state=tk.NORMAL)
        if success:
            self.status_label.config(text="✅ 下载完成", foreground="green")
            self._update_status()
        else:
            self.status_label.config(text="❌ 下载失败", foreground="red")

    def get_current_model(self):
        """获取当前选中的模型配置"""
        choice = self._get_current_choice()
        return settings.get_model_by_choice(choice)

    def get_frame(self):
        return self.frame