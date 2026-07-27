#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
视频生成工作室 - Tkinter 纯桌面版
无 Web，无浏览器
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from core.generator import generator
from utils.logger import get_logger

logger = get_logger(__name__)


class VideoGenApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎬 本地视频生成工作室")
        self.root.geometry("950x820")
        self.root.minsize(850, 750)
        self.root.configure(bg='#f0f0f0')

        self.is_generating = False
        self.cancel_flag = False

        Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        Path(settings.MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)

        self._create_widgets()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        logger.info("=" * 60)
        logger.info("🎬 本地视频生成工作室 (Tkinter 桌面版)")
        logger.info(f"   输出: {settings.OUTPUT_DIR}")
        logger.info("=" * 60)

    def _create_widgets(self):
        """创建所有控件"""
        main = ttk.Frame(self.root, padding="10")
        main.pack(fill=tk.BOTH, expand=True)

        # ===== 标题 =====
        ttk.Label(main, text="🎬 本地视频生成工作室", font=("微软雅黑", 16, "bold")).pack(anchor=tk.W, pady=(0, 5))
        ttk.Label(main, text="基于 CogVideoX · 纯CPU运行 · 32GB内存优化", font=("微软雅黑", 9), foreground="gray").pack(anchor=tk.W, pady=(0, 10))

        # ===== 提示词 =====
        prompt_frame = ttk.LabelFrame(main, text="📝 提示词", padding="10")
        prompt_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(prompt_frame, text="正面提示词:").pack(anchor=tk.W)
        self.prompt_text = tk.Text(prompt_frame, height=4, wrap=tk.WORD, font=("微软雅黑", 10))
        self.prompt_text.pack(fill=tk.X, pady=(5, 10))
        self.prompt_text.insert("1.0", "A serene landscape with mountains and a river flowing through a valley, sunset lighting, 8k, highly detailed")

        ttk.Label(prompt_frame, text="负面提示词:").pack(anchor=tk.W)
        self.neg_text = tk.Text(prompt_frame, height=2, wrap=tk.WORD, font=("微软雅黑", 10))
        self.neg_text.pack(fill=tk.X, pady=(5, 0))
        self.neg_text.insert("1.0", "worst quality, low quality, blurry, distorted, deformed, ugly, bad anatomy")


        # ===== 模型选择 =====
        model_frame = ttk.LabelFrame(main, text="🤖 模型选择", padding="10")
        model_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(model_frame, text="选择模型:").pack(side=tk.LEFT, padx=(0, 10))

        self.model_choice_var = tk.StringVar(value=settings.MODEL_CHOICE)
        model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.model_choice_var,
            values=["cogvideox-1b (约1.7GB, 快速)", "cogvideox-2b (约5GB, 高质量)"],
            width=35,
            state="readonly"
        )
        model_combo.pack(side=tk.LEFT, padx=(0, 10))
        model_combo.bind('<<ComboboxSelected>>', self._on_model_changed)

        self.model_status_label = ttk.Label(model_frame, text="", foreground="gray")
        self.model_status_label.pack(side=tk.LEFT)

        # 检查当前模型是否存在
        self._update_model_status()

        # ===== 参数 =====
        param_frame = ttk.LabelFrame(main, text="⚙️ 生成参数", padding="10")
        param_frame.pack(fill=tk.X, pady=(0, 10))

        # 第一行
        row1 = ttk.Frame(param_frame)
        row1.pack(fill=tk.X, pady=2)

        ttk.Label(row1, text="步数:").pack(side=tk.LEFT, padx=(0, 5))
        self.steps_var = tk.IntVar(value=50)
        ttk.Spinbox(row1, from_=20, to=100, textvariable=self.steps_var, width=6, increment=5).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(row1, text="CFG:").pack(side=tk.LEFT, padx=(0, 5))
        self.cfg_var = tk.DoubleVar(value=6.0)
        ttk.Spinbox(row1, from_=1.0, to=12.0, textvariable=self.cfg_var, width=6, increment=0.5).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(row1, text="FPS:").pack(side=tk.LEFT, padx=(0, 5))
        self.fps_var = tk.IntVar(value=8)
        ttk.Spinbox(row1, from_=4, to=15, textvariable=self.fps_var, width=6, increment=1).pack(side=tk.LEFT)

        # 第二行
        row2 = ttk.Frame(param_frame)
        row2.pack(fill=tk.X, pady=2)

        ttk.Label(row2, text="宽度:").pack(side=tk.LEFT, padx=(0, 5))
        self.width_var = tk.IntVar(value=576)
        ttk.Spinbox(row2, from_=256, to=768, textvariable=self.width_var, width=6, increment=32).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(row2, text="高度:").pack(side=tk.LEFT, padx=(0, 5))
        self.height_var = tk.IntVar(value=320)
        ttk.Spinbox(row2, from_=256, to=768, textvariable=self.height_var, width=6, increment=32).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(row2, text="帧数:").pack(side=tk.LEFT, padx=(0, 5))
        self.frames_var = tk.IntVar(value=49)
        ttk.Spinbox(row2, from_=25, to=85, textvariable=self.frames_var, width=6, increment=4).pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(row2, text="种子:").pack(side=tk.LEFT, padx=(0, 5))
        self.seed_var = tk.IntVar(value=-1)
        ttk.Spinbox(row2, from_=-1, to=999999, textvariable=self.seed_var, width=8).pack(side=tk.LEFT)

        # ===== 按钮 =====
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.generate_btn = ttk.Button(btn_frame, text="🚀 生成视频", command=self._start_generation, width=15)
        self.generate_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.cancel_btn = ttk.Button(btn_frame, text="⏹️ 取消", command=self._cancel_generation, state=tk.DISABLED, width=15)
        self.cancel_btn.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(btn_frame, text="📁 打开输出目录", command=self._open_output_dir, width=15).pack(side=tk.LEFT)

        # ===== 进度 =====
        progress_frame = ttk.LabelFrame(main, text="📊 进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.pack(fill=tk.X)

        self.status_label = ttk.Label(progress_frame, text="就绪", foreground="blue")
        self.status_label.pack(anchor=tk.W, pady=(5, 0))

        # ===== 视频预览 =====
        preview_frame = ttk.LabelFrame(main, text="🎬 视频预览", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True)

        self.preview_label = ttk.Label(preview_frame, text="生成后将在这里显示视频预览", foreground="gray")
        self.preview_label.pack(expand=True)

        # 底部提示
        ttk.Label(main, text="💡 纯CPU模式生成约需5-15分钟，请耐心等待", foreground="gray", font=("微软雅黑", 8)).pack(anchor=tk.W, pady=(5, 0))

    def _on_model_changed(self, event):
        """模型切换"""
        choice = self.model_choice_var.get()
        if "1b" in choice.lower():
            model_type = "cogvideox-1b"
            model_name = "ZhipuAI/CogVideoX-1b"
            model_path = Path(settings.BASE_DIR) / "models" / "ZhipuAI" / "CogVideoX-1b"
        else:
            model_type = "cogvideox-2b"
            model_name = "ZhipuAI/CogVideoX-2b"
            model_path = Path(settings.BASE_DIR) / "models" / "ZhipuAI" / "CogVideoX-2b"
        
        # 更新 settings
        settings.MODEL_CHOICE = model_type
        settings.MODEL_NAME = model_name
        settings.MODEL_PATH = str(model_path)
        
        # 卸载旧模型
        if model_loader.is_loaded():
            model_loader.unload_model()
        
        self._update_model_status()
        self.status_label.config(text=f"已切换到 {choice}，请重新生成")
        logger.info(f"🔄 切换到模型: {choice}")

    def _update_model_status(self):
        """更新模型状态显示"""
        model_path = Path(settings.MODEL_PATH)
        if model_path.exists():
            size_gb = sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file()) / 1024 / 1024 / 1024
            self.model_status_label.config(
                text=f"✅ 已下载 ({size_gb:.1f}GB)",
                foreground="green"
            )
        else:
            self.model_status_label.config(
                text="❌ 未下载，请运行 scripts/download_model.py",
                foreground="red"
            )
        
    def _start_generation(self):
        if self.is_generating:
            return

        prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showwarning("提示", "请输入正面提示词")
            return

        params = {
            "prompt": prompt,
            "negative_prompt": self.neg_text.get("1.0", tk.END).strip(),
            "num_steps": self.steps_var.get(),
            "guidance_scale": self.cfg_var.get(),
            "fps": self.fps_var.get(),
            "width": self.width_var.get(),
            "height": self.height_var.get(),
            "num_frames": self.frames_var.get(),
            "seed": self.seed_var.get() if self.seed_var.get() != -1 else None,
        }

        self.is_generating = True
        self.cancel_flag = False
        self.generate_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_label.config(text="🚀 开始生成...")

        thread = threading.Thread(target=self._generate_thread, args=(params,), daemon=True)
        thread.start()

    def _generate_thread(self, params):
        try:
            def progress_cb(progress, msg):
                self.root.after(0, lambda: self.progress_var.set(progress))
                self.root.after(0, lambda: self.status_label.config(text=msg))

            def cancel_cb():
                return self.cancel_flag

            video_path = generator.generate(
                prompt=params["prompt"],
                negative_prompt=params["negative_prompt"],
                num_frames=params["num_frames"],
                fps=params["fps"],
                width=params["width"],
                height=params["height"],
                guidance_scale=params["guidance_scale"],
                num_inference_steps=params["num_steps"],
                seed=params["seed"],
                progress_callback=progress_cb,
                cancel_callback=cancel_cb,
            )

            self.root.after(0, lambda: self._on_complete(str(video_path)))

        except InterruptedError:
            self.root.after(0, self._on_cancelled)
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self._on_error(error_msg))
        finally:
            self.is_generating = False
            self.root.after(0, lambda: self.generate_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.cancel_btn.config(state=tk.DISABLED))

    def _on_complete(self, video_path):
        self.progress_var.set(100)
        self.status_label.config(text="✅ 生成完成!")
        self.preview_label.config(text=f"✅ 视频已保存\n📁 {os.path.basename(video_path)}")
        messagebox.showinfo("完成", f"视频已保存:\n{video_path}")

    def _on_error(self, error):
        self.status_label.config(text=f"❌ 错误: {error}")
        messagebox.showerror("错误", f"生成失败:\n{error}")

    def _on_cancelled(self):
        self.status_label.config(text="⏹️ 已取消")

    def _cancel_generation(self):
        self.cancel_flag = True
        self.cancel_btn.config(state=tk.DISABLED)
        self.status_label.config(text="⏹️ 正在取消...")

    def _open_output_dir(self):
        output_dir = settings.OUTPUT_DIR
        if os.path.exists(output_dir):
            os.startfile(output_dir)

    def _on_close(self):
        if self.is_generating:
            if not messagebox.askyesno("确认", "视频正在生成，确定退出吗？"):
                return
            self.cancel_flag = True
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    app = VideoGenApp()
    app.run()


if __name__ == "__main__":
    main()