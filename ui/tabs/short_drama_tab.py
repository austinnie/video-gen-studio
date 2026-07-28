#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
短剧生成标签页 - 使用任务队列
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from pathlib import Path

from core.short_drama import short_drama_generator
from core.task_queue import task_queue
from utils.logger import get_logger

logger = get_logger(__name__)


class ShortDramaTab:
    """短剧生成标签页"""
    
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.frame = ttk.Frame(parent)
        self.is_generating = False
        self.cancel_flag = False
        self._current_task_id = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """构建 UI"""
        frame = self.frame
        row = 0
        
        ttk.Label(
            frame,
            text="🎬 AI 短剧生成 (小说 → 视频)",
            font=("微软雅黑", 14, "bold")
        ).grid(row=row, column=0, columnspan=3, sticky=tk.W, padx=5, pady=10)
        row += 1
        
        # 操作按钮
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        ttk.Button(btn_frame, text="📁 加载小说文件", command=self._load_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📝 粘贴小说", command=self._paste_text).pack(side=tk.LEFT, padx=5)
        
        self.file_label = ttk.Label(btn_frame, text="", foreground="gray")
        self.file_label.pack(side=tk.LEFT, padx=10)
        row += 1
        
        # 小说内容
        ttk.Label(frame, text="📖 小说内容:").grid(row=row, column=0, sticky=tk.W, padx=5)
        row += 1
        
        self.text_area = tk.Text(frame, height=12, width=80, wrap=tk.WORD)
        self.text_area.grid(
            row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S),
            padx=5, pady=5
        )
        row += 1
        
        # 标题输入
        title_frame = ttk.Frame(frame)
        title_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        ttk.Label(title_frame, text="作品标题:").pack(side=tk.LEFT, padx=5)
        self.title_var = tk.StringVar(value="我的AI短剧")
        ttk.Entry(title_frame, textvariable=self.title_var, width=30).pack(side=tk.LEFT, padx=5)
        row += 1
        
        # 生成按钮
        btn_frame2 = ttk.Frame(frame)
        btn_frame2.grid(row=row, column=0, columnspan=3, pady=10)
        
        self.generate_btn = ttk.Button(
            btn_frame2,
            text="🚀 生成短剧",
            command=self._queue_generation,
            width=15
        )
        self.generate_btn.pack(side=tk.LEFT, padx=10)
        
        self.cancel_btn = ttk.Button(
            btn_frame2,
            text="⏹️ 取消",
            command=self._cancel_generation,
            state=tk.DISABLED,
            width=15
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(btn_frame2, text="📁 打开输出", command=self._open_output, width=15).pack(side=tk.LEFT, padx=10)
        row += 1
        
        # 进度
        progress_frame = ttk.LabelFrame(frame, text="📊 生成进度", padding=5)
        progress_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5, padx=5)
        row += 1
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="就绪", foreground="blue")
        self.status_label.pack(anchor=tk.W, pady=2)
        
        # 分镜列表
        preview_frame = ttk.LabelFrame(frame, text="📋 分镜列表", padding=5)
        preview_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)
        
        self.shots_listbox = tk.Listbox(preview_frame, height=5)
        self.shots_listbox.pack(fill=tk.BOTH, expand=True)
        
        frame.rowconfigure(row, weight=1)
        frame.columnconfigure(1, weight=1)
    
    def _queue_generation(self):
        """将短剧生成任务加入队列"""
        if self.is_generating:
            return
        
        text = self.text_area.get("1.0", tk.END).strip()
        if not text or len(text) < 20:
            messagebox.showwarning("提示", "请至少输入20字以上的小说内容")
            return
        
        title = self.title_var.get().strip() or "我的AI短剧"
        
        # 检查队列状态
        status = task_queue.get_status()
        if status["is_running"]:
            queue_len = status["queue_length"]
            current_name = status["current_task"]["name"] if status["current_task"] else "未知"
            if not messagebox.askyesno(
                "提示",
                f"当前有任务正在执行: {current_name}\n"
                f"队列中还有 {queue_len} 个任务等待\n\n"
                "是否将短剧生成任务加入队列？\n"
                f"预计耗时: 5-10 小时"
            ):
                return
        
        self.is_generating = True
        self.cancel_flag = False
        self.generate_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.status_label.config(text="📋 任务已入队，等待执行...")
        self.shots_listbox.delete(0, tk.END)
        
        def progress_cb(progress, msg):
            self.app.root.after(0, lambda: self.progress_var.set(progress))
            self.app.root.after(0, lambda: self.status_label.config(text=msg))
        
        def cancel_cb():
            return self.cancel_flag
        
        def short_drama_task():
            try:
                video_path = short_drama_generator.generate_from_text(
                    text=text,
                    title=title,
                    progress_callback=progress_cb,
                    cancel_callback=cancel_cb,
                )
                self.app.root.after(0, lambda: self._on_complete(str(video_path)))
            except InterruptedError:
                self.app.root.after(0, self._on_cancel)
            except Exception as e:
                self.app.root.after(0, lambda: self._on_error(str(e)))
            finally:
                self.is_generating = False
                self.app.root.after(0, lambda: self.generate_btn.config(state=tk.NORMAL))
                self.app.root.after(0, lambda: self.cancel_btn.config(state=tk.DISABLED))
        
        # 加入队列
        task = task_queue.add_task("AI短剧", short_drama_task)
        self._current_task_id = task.id
    
    def _load_file(self):
        """加载小说文件"""
        filepath = filedialog.askopenfilename(
            title="选择小说文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.text_area.delete("1.0", tk.END)
                self.text_area.insert("1.0", content)
                self.file_label.config(text=Path(filepath).name)
                self.title_var.set(Path(filepath).stem)
            except Exception as e:
                messagebox.showerror("错误", f"读取文件失败:\n{e}")
    
    def _paste_text(self):
        """粘贴小说内容"""
        try:
            text = self.app.root.clipboard_get()
            if text:
                self.text_area.delete("1.0", tk.END)
                self.text_area.insert("1.0", text)
        except:
            pass
    
    def _on_complete(self, video_path):
        """生成完成"""
        self.progress_var.set(100)
        self.status_label.config(text=f"✅ 短剧生成完成!\n📁 {video_path}")
        messagebox.showinfo("完成", f"短剧已生成:\n{video_path}")
    
    def _on_error(self, error):
        self.status_label.config(text=f"❌ 错误: {error}")
        messagebox.showerror("错误", f"生成失败:\n{error}")
    
    def _on_cancel(self):
        self.status_label.config(text="⏹️ 已取消")
    
    def _cancel_generation(self):
        """取消生成"""
        self.cancel_flag = True
        short_drama_generator.cancel()
        task_queue.cancel_current()
        self.cancel_btn.config(state=tk.DISABLED)
        self.status_label.config(text="⏹️ 正在取消...")
    
    def _open_output(self):
        """打开输出目录"""
        import os
        output_dir = Path(settings.OUTPUT_DIR)
        if output_dir.exists():
            os.startfile(str(output_dir))
    
    def get_frame(self):
        return self.frame