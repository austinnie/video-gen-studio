import tkinter as tk
from tkinter import ttk, messagebox
import threading
from pathlib import Path

from config.settings import settings
from core.generator import generator
from core.task_queue import task_queue
from utils.logger import get_logger
from utils.reloader import reloader

from ui.widgets.prompt import PromptWidget
from ui.widgets.model import ModelWidget
from ui.widgets.params import ParamsWidget
from ui.widgets.progress import ProgressWidget
from ui.widgets.preview import PreviewWidget
from ui.tabs.short_drama_tab import ShortDramaTab

logger = get_logger(__name__)


class VideoGenApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎬 本地视频生成工作室")
        self.root.geometry("950x820")
        self.root.configure(bg='#f0f0f0')

        self.is_generating = False
        self.cancel_flag = False

        Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

        reloader.set_rebuild_callback(self._rebuild_ui)

        self.main = ttk.Frame(self.root, padding="10")
        self.main.pack(fill=tk.BOTH, expand=True)

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        """构建 UI"""
        main = self.main

        # 标题
        title_frame = ttk.Frame(main)
        title_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(title_frame, text="🎬 本地视频生成工作室", font=("微软雅黑", 16, "bold")).pack(side=tk.LEFT)
        ttk.Label(title_frame, text="多模型支持 · 纯CPU · 32GB优化", font=("微软雅黑", 9), foreground="gray").pack(side=tk.LEFT, padx=10)

        # ===== 队列状态 =====
        self.queue_frame = ttk.Frame(main)
        self.queue_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.queue_status = ttk.Label(
            self.queue_frame,
            text="📋 队列空闲",
            foreground="green",
            font=("微软雅黑", 9)
        )
        self.queue_status.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            self.queue_frame,
            text="💡 任务自动排队，请勿同时执行多个生成",
            foreground="gray",
            font=("微软雅黑", 8)
        ).pack(side=tk.LEFT, padx=15)

        # ===== Notebook =====
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # 文生图标签页
        txt_frame = ttk.Frame(self.notebook)
        self.notebook.add(txt_frame, text="📝 文生图")
        self._build_txt_tab(txt_frame)

        # AI短剧标签页
        self.short_drama_tab = ShortDramaTab(self.notebook, self)
        self.notebook.add(self.short_drama_tab.get_frame(), text="🎬 AI短剧")

        # 更新队列状态
        self._update_queue_status()

    def _build_txt_tab(self, parent):
        """构建文生图标签页"""
        self.prompt = PromptWidget(parent)
        self.model = ModelWidget(parent, self._on_model_changed)
        self.params = ParamsWidget(parent, self.model)
        self._build_buttons(parent)
        self.progress = ProgressWidget(parent)
        self.preview = PreviewWidget(parent)

    def _build_buttons(self, parent):
        """构建按钮"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 10))

        self.gen_btn = ttk.Button(
            frame,
            text="🚀 生成",
            command=self._queue_generation,
            width=12
        )
        self.gen_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.cancel_btn = ttk.Button(
            frame,
            text="⏹️ 取消",
            command=self._cancel_generation,
            state=tk.DISABLED,
            width=12
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(frame, text="🔄 热重载", command=self._hot_reload, width=12).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(frame, text="📁 打开输出", command=self._open_output, width=12).pack(side=tk.LEFT)

        self.memory_label = ttk.Label(frame, text="", foreground="gray", font=("", 8))
        self.memory_label.pack(side=tk.RIGHT)
        self._update_memory()

    def _queue_generation(self):
        """将生成任务加入队列"""
        prompt = self.prompt.get_prompt()
        if not prompt:
            messagebox.showwarning("提示", "请输入正面提示词")
            return

        params = self.params.get_params()
        params["prompt"] = prompt
        params["negative_prompt"] = self.prompt.get_negative()

        model = self.model.get_current_model()
        if model:
            model_path = Path(settings.BASE_DIR) / "models" / model.local_dir
            if not model_path.exists():
                if not messagebox.askyesno("提示", f"模型 {model.name} 未下载，是否立即下载？"):
                    return
                self.model._download()
                return

        # 检查是否有任务正在运行
        status = task_queue.get_status()
        if status["is_running"]:
            queue_len = status["queue_length"]
            current_name = status["current_task"]["name"] if status["current_task"] else "未知"
            if not messagebox.askyesno(
                "提示",
                f"当前有任务正在执行: {current_name}\n"
                f"队列中还有 {queue_len} 个任务等待\n\n"
                "是否将当前任务加入队列？"
            ):
                return

        # 禁用按钮
        self.gen_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress.update(0, "📋 任务已入队，等待执行...")

        # 定义任务函数
        def generate_task():
            try:
                def cb(progress, msg):
                    self.root.after(0, lambda: self.progress.update(progress, msg))

                def cancel_cb():
                    return self.cancel_flag

                path = generator.generate(
                    prompt=params["prompt"],
                    negative_prompt=params["negative_prompt"],
                    num_frames=params["frames"],
                    fps=params["fps"],
                    width=params["width"],
                    height=params["height"],
                    guidance_scale=params["cfg"],
                    num_inference_steps=params["steps"],
                    seed=params["seed"],
                    progress_callback=cb,
                    cancel_callback=cancel_cb,
                )
                return path
            except InterruptedError:
                raise
            except Exception as e:
                raise

        # 加入队列
        task = task_queue.add_task("文生图", generate_task)
        self._current_task_id = task.id

        # 启动监控线程
        threading.Thread(target=self._monitor_task, args=(task,), daemon=True).start()

    def _monitor_task(self, task):
        """监控任务执行"""
        import time
        while True:
            status = task_queue.get_status()
            
            if not status["is_running"] and status["current_task"] is None:
                # 任务完成
                self.root.after(0, self._on_task_complete)
                break
            
            current = status["current_task"]
            if current and current.get("name") == task.name:
                self.root.after(0, lambda: self.progress.update(
                    current.get("progress", 0),
                    current.get("message", "执行中...")
                ))
            
            time.sleep(1)

    def _on_task_complete(self):
        """任务完成"""
        self.is_generating = False
        self.gen_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.progress.update(100, "✅ 任务完成")
        self._update_queue_status()
        messagebox.showinfo("完成", "生成任务已完成！")

    def _cancel_generation(self):
        """取消当前任务"""
        self.cancel_flag = True
        generator.cancel()
        task_queue.cancel_current()
        self.cancel_btn.config(state=tk.DISABLED)
        self.gen_btn.config(state=tk.NORMAL)
        self.progress.update(0, "⏹️ 已取消")
        self._update_queue_status()

    def _update_queue_status(self):
        """更新队列状态"""
        status = task_queue.get_status()
        if status["is_running"]:
            current = status["current_task"]
            name = current["name"] if current else "未知"
            self.queue_status.config(
                text=f"▶️ 执行中: {name} (队列: {status['queue_length']})",
                foreground="orange"
            )
        elif status["queue_length"] > 0:
            self.queue_status.config(
                text=f"📋 等待中: {status['queue_length']} 个任务",
                foreground="blue"
            )
        else:
            self.queue_status.config(text="📋 队列空闲", foreground="green")

    def _on_model_changed(self, msg):
        if hasattr(self, 'params'):
            self.params.refresh_defaults()
        if hasattr(self, 'progress'):
            self.progress.update(0, f"🔄 {msg}")

    def _hot_reload(self):
        if self.is_generating and not messagebox.askyesno("确认", "生成中，确定重载？"):
            return
        if not messagebox.askyesno("确认", "确定热重载？"):
            return
        self.progress.update(0, "🔄 热重载中...")
        reloader.reload_all()

    def _rebuild_ui(self):
        for child in self.main.winfo_children():
            child.destroy()
        self._build_ui()
        if hasattr(self, 'model'):
            self.model._update_status()
        self.root.update_idletasks()

    def _open_output(self):
        import os
        if os.path.exists(settings.OUTPUT_DIR):
            os.startfile(settings.OUTPUT_DIR)

    def _update_memory(self):
        try:
            import psutil
            m = psutil.virtual_memory()
            self.memory_label.config(text=f"💾 {m.used/1024**3:.1f}/{m.total/1024**3:.1f}GB")
        except:
            pass
        self.root.after(5000, self._update_memory)

    def _on_close(self):
        if self.is_generating and not messagebox.askyesno("确认", "生成中，确定退出？"):
            return
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    app = VideoGenApp()
    app.run()


if __name__ == "__main__":
    main()