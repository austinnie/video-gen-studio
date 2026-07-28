#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
视频生成核心类 - 支持真正取消
"""

import torch
import time
import gc
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from diffusers.utils import export_to_video

from config.settings import settings
from core.model_loader import model_loader
from utils.logger import get_logger
from utils.memory import log_memory_usage, ensure_memory_available
from utils.ffmpeg_utils import post_process_video

logger = get_logger(__name__)


class VideoGenerator:
    """视频生成核心类 - 支持真正取消"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.pipeline = None
        self.is_generating = False
        self.cancel_flag = False
        self._generation_id = None
        self._current_step = 0
        self._total_steps = 0
        self._lock = threading.Lock()
        self._generation_thread = None
    
    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        num_frames: int = 30,
        fps: int = 8,
        width: int = 576,
        height: int = 320,
        guidance_scale: float = 7.5,
        num_inference_steps: int = 50,
        seed: Optional[int] = None,
        progress_callback: Optional[Callable] = None,
        cancel_callback: Optional[Callable] = None,
        generation_id: str = None,
    ) -> Path:
        """生成视频 - 支持取消"""
        
        # 检查是否已有生成任务
        with self._lock:
            if self.is_generating:
                raise RuntimeError("已有生成任务进行中，请等待完成")
            self.is_generating = True
            self.cancel_flag = False
        
        self._generation_id = generation_id or datetime.now().strftime("%H%M%S")
        self._current_step = 0
        self._total_steps = num_inference_steps
        
        try:
            # 检查内存
            if not ensure_memory_available(settings.MEMORY_WARNING_THRESHOLD):
                logger.warning("内存不足，生成可能失败")

            # 加载模型
            if self.pipeline is None:
                self.pipeline = model_loader.load_model(progress_callback)

            if self.pipeline is None:
                raise RuntimeError("模型加载失败")

            # 设置种子
            if seed is None:
                import random
                seed = random.randint(1, 2**32 - 1)

            generator = torch.Generator("cpu").manual_seed(seed)

            logger.info(f"🎬 开始生成视频... (ID: {self._generation_id})")
            logger.info(f"   Prompt: {prompt}")
            logger.info(f"   帧数: {num_frames}, FPS: {fps}")
            logger.info(f"   尺寸: {width}x{height}")
            logger.info(f"   步数: {num_inference_steps}, CFG: {guidance_scale}")
            logger.info(f"   种子: {seed}")
            log_memory_usage()

            if progress_callback:
                progress_callback(10, "开始推理...")

            # ===== 执行生成 =====
            with torch.no_grad():
                # 检查是否支持回调
                if hasattr(self.pipeline.__class__, 'callback_on_step_end'):
                    # CogVideoX 系列
                    result = self.pipeline(
                        prompt=prompt,
                        negative_prompt=negative_prompt or None,
                        num_frames=num_frames,
                        width=width,
                        height=height,
                        guidance_scale=guidance_scale,
                        num_inference_steps=num_inference_steps,
                        generator=generator,
                        callback_on_step_end=self._create_step_callback(
                            num_inference_steps, progress_callback, cancel_callback
                        ),
                    )
                else:
                    # DiffusionPipeline (Zeroscope)
                    # 使用 callback 参数
                    result = self.pipeline(
                        prompt=prompt,
                        negative_prompt=negative_prompt or None,
                        num_frames=num_frames,
                        width=width,
                        height=height,
                        guidance_scale=guidance_scale,
                        num_inference_steps=num_inference_steps,
                        generator=generator,
                        callback=self._create_diffusion_callback(
                            num_inference_steps, progress_callback, cancel_callback
                        ),
                        callback_steps=1,
                    )

            if progress_callback:
                progress_callback(85, "导出视频...")

            # 检查是否取消
            if self.cancel_flag:
                raise InterruptedError("用户取消")

            if cancel_callback and cancel_callback():
                raise InterruptedError("用户取消")

            # 导出视频
            video_frames = result.frames[0]

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in " _-") or "video"
            filename = f"{timestamp}_{safe_prompt}.mp4"
            output_path = Path(settings.OUTPUT_DIR) / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)

            export_to_video(video_frames, str(output_path), fps=fps)

            if progress_callback:
                progress_callback(95, "后处理...")

            final_path = post_process_video(
                output_path,
                prompt=prompt,
                add_watermark=False
            )

            if progress_callback:
                progress_callback(100, "✅ 完成！")

            logger.info(f"✅ 视频已保存: {final_path}")
            log_memory_usage()

            return final_path

        except InterruptedError:
            logger.info(f"⏹️ 生成被取消 (ID: {self._generation_id})")
            raise
        except Exception as e:
            logger.error(f"生成失败: {e}")
            raise
        finally:
            with self._lock:
                self.is_generating = False
            
            # 清理内存
            try:
                import gc
                gc.collect()
                if hasattr(torch, 'cuda') and torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
            log_memory_usage()

    def _create_step_callback(self, total_steps, progress_callback, cancel_callback):
        """创建步骤回调 (CogVideoX 专用)"""
        def callback(pipe, step, timestep, callback_kwargs):
            # 检查取消
            if self.cancel_flag:
                raise InterruptedError("用户取消")
            if cancel_callback and cancel_callback():
                self.cancel_flag = True
                raise InterruptedError("用户取消")
            
            self._current_step = step + 1
            
            if progress_callback and step % 2 == 0:
                progress = 10 + (step / total_steps) * 70
                progress_callback(int(progress), f"推理中 {step+1}/{total_steps}")
            return callback_kwargs
        return callback

    def _create_diffusion_callback(self, total_steps, progress_callback, cancel_callback):
        """创建 DiffusionPipeline 回调"""
        def callback(step, timestep, latents):
            # 检查取消
            if self.cancel_flag:
                raise InterruptedError("用户取消")
            if cancel_callback and cancel_callback():
                self.cancel_flag = True
                raise InterruptedError("用户取消")
            
            self._current_step = step + 1
            
            if progress_callback and step % 2 == 0:
                progress = 10 + (step / total_steps) * 70
                progress_callback(int(progress), f"推理中 {step+1}/{total_steps}")
        return callback

    def cancel(self):
        """取消生成 - 立即生效"""
        with self._lock:
            self.cancel_flag = True
            self.is_generating = False
        
        logger.info(f"⏹️ 取消生成 (ID: {self._generation_id})")
        
        # 清理内存
        try:
            import gc
            gc.collect()
            if hasattr(torch, 'cuda') and torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass

    def is_running(self) -> bool:
        """检查是否正在生成"""
        with self._lock:
            return self.is_generating

    def get_progress(self) -> dict:
        """获取当前进度"""
        return {
            "is_running": self.is_generating,
            "current_step": self._current_step,
            "total_steps": self._total_steps,
            "generation_id": self._generation_id,
            "cancel_flag": self.cancel_flag,
        }


# 全局生成器实例
generator = VideoGenerator()