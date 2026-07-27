import tkinter as tk
from tkinter import ttk, messagebox
import threading
from pathlib import Path

from config.settings import settings
from core.generator import generator
from utils.logger import get_logger
from utils.reloader import reloader

from ui.widgets.prompt import PromptWidget
from ui.widgets.model import ModelWidget
from ui.widgets.params import ParamsWidget
from ui.widgets.progress import ProgressWidget
from ui.widgets.preview import PreviewWidget

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

        # 创建主框架
        self.main = ttk.Frame(self.root, padding="10")
        self.main.pack(fill=tk.BOTH, expand=True)

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        """构建 UI - 可被热重载调用"""
        main = self.main

        # 标题
        title_frame = ttk.Frame(main)
        title_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(title_frame, text="🎬 本地视频生成工作室", font=("微软雅黑", 16, "bold")).pack(side=tk.LEFT)
        ttk.Label(title_frame, text="多模型支持 · 纯CPU · 32GB优化", font=("微软雅黑", 9), foreground="gray").pack(side=tk.LEFT, padx=10)

        # 提示词
        self.prompt = PromptWidget(main)

        # 模型选择
        self.model = ModelWidget(main, self._on_model_changed)

        # 参数
        self.params = ParamsWidget(main, self.model)

        # 按钮
        self._build_buttons(main)

        # 进度
        self.progress = ProgressWidget(main)

        # 预览
        self.preview = PreviewWidget(main)

    def _build_buttons(self, parent):
        """构建按钮"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=(0, 10))

        self.gen_btn = ttk.Button(frame, text="🚀 生成", command=self._start_generation, width=12)
        self.gen_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.cancel_btn = ttk.Button(frame, text="⏹️ 取消", command=self._cancel_generation, state=tk.DISABLED, width=12)
        self.cancel_btn.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(frame, text="🔄 热重载", command=self._hot_reload, width=12).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(frame, text="📁 打开输出", command=self._open_output, width=12).pack(side=tk.LEFT)

        self.memory_label = ttk.Label(frame, text="", foreground="gray", font=("", 8))
        self.memory_label.pack(side=tk.RIGHT)
        self._update_memory()

    def _rebuild_ui(self):
        """重建 UI（由 reloader 调用）"""
        # 清空 main 框架的所有子控件
        for child in self.main.winfo_children():
            child.destroy()

        # 重新构建 UI
        self._build_ui()

        # 更新模型状态
        if hasattr(self, 'model'):
            self.model._update_status()

        # 强制刷新界面
        self.root.update_idletasks()

    def _on_model_changed(self, msg):
        """模型切换回调"""
        if hasattr(self, 'params'):
            self.params.refresh_defaults()
        if hasattr(self, 'progress'):
            self.progress.update(0, f"🔄 {msg}")

    # ===== 生成方法 =====

    def _start_generation(self):
        if self.is_generating:
            return

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

        self.is_generating = True
        self.cancel_flag = False
        self.gen_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress.reset()

        threading.Thread(target=self._generate_thread, args=(params,), daemon=True).start()

    def _generate_thread(self, params):
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
            self.root.after(0, lambda: self._on_done(str(path)))
        except InterruptedError:
            self.root.after(0, self._on_cancel)
        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda: self._on_error(error_msg))
        finally:
            self.is_generating = False
            self.root.after(0, lambda: self.gen_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.cancel_btn.config(state=tk.DISABLED))

    def _on_done(self, path):
        self.progress.update(100, "✅ 完成")
        self.preview.show_video(path)
        messagebox.showinfo("完成", f"视频已保存:\n{path}")

    def _on_error(self, msg):
        self.progress.update(0, f"❌ {msg}")
        messagebox.showerror("错误", f"生成失败:\n{msg}")

    def _on_cancel(self):
        self.progress.update(0, "⏹️ 已取消")

    def _cancel_generation(self):
        self.cancel_flag = True
        self.cancel_btn.config(state=tk.DISABLED)

    # ===== 热重载 =====

    def _hot_reload(self):
        """手动热重载"""
        if self.is_generating:
            if not messagebox.askyesno("确认", "视频正在生成中，热重载将中断生成，确定继续吗？"):
                return
            self.cancel_flag = True
            self.is_generating = False

        if not messagebox.askyesno("确认", "确定要热重载吗？\n\n将重新加载所有模块并刷新界面。"):
            return

        self.progress.update(0, "🔄 热重载中...")
        self.root.update()

        success_list, failed_list = reloader.reload_all()

        if failed_list:
            self.progress.update(0, f"⚠️ 热重载完成，{len(failed_list)} 个模块失败")
            messagebox.showwarning("热重载", f"部分模块重载失败:\n{', '.join(failed_list[:5])}")
        else:
            self.progress.update(100, f"✅ 热重载完成 (已重载 {len(success_list)} 个模块)")

    # ===== 工具 =====

    def _open_output(self):
        import os
        if os.path.exists(settings.OUTPUT_DIR):
            os.startfile(settings.OUTPUT_DIR)

    # 在 _build_buttons 或 _update_memory 中
    def _update_memory(self):
        """更新内存状态 - 从 memory_monitor 获取"""
        try:
            status = memory_monitor.get_status()
            mem = status.get("memory", {})
            if mem:
                used = mem.get('process_rss_gb', 0)
                total = mem.get('system_total_gb', 0)
                self.memory_label.config(text=f"💾 {used:.1f}/{total:.1f}GB")
            else:
                import psutil
                m = psutil.virtual_memory()
                self.memory_label.config(text=f"💾 {m.used/1024**3:.1f}/{m.total/1024**3:.1f}GB")
        except:
            pass
        self.root.after(60000, self._update_memory)  # 每60秒更新

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