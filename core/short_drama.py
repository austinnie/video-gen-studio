#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
短剧生成器 - 使用任务队列
"""

import os
import time
import threading
from pathlib import Path
from typing import Optional, Callable, List, Dict
from datetime import datetime

from config.settings import settings
from core.script_processor import Script, Shot, script_processor
from core.generator import generator
from core.task_queue import task_queue
from utils.logger import get_logger
from utils.memory import log_memory_usage

logger = get_logger(__name__)


class ShortDramaGenerator:
    """短剧生成器 - 使用任务队列"""
    
    def __init__(self):
        self.is_generating = False
        self.cancel_flag = False
        self.current_script = None
        self.generated_shots = []
        self.output_dir = None
        self._task_id = None
    
    def generate_from_text(
        self,
        text: str,
        title: str = "",
        progress_callback: Optional[Callable] = None,
        cancel_callback: Optional[Callable] = None,
    ) -> Path:
        """
        从小说文本生成短剧（通过任务队列）
        """
        self.is_generating = True
        self.cancel_flag = False
        self.generated_shots = []
        
        try:
            # 1. 处理剧本
            if progress_callback:
                progress_callback(5, "📝 正在拆解剧本...")
            
            script = script_processor.process(text, title)
            self.current_script = script
            
            logger.info(f"📋 剧本拆解完成: {len(script.shots)} 个分镜")
            
            if not script.shots:
                raise ValueError("剧本拆解失败，没有分镜")
            
            # 2. 创建输出目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = Path(settings.OUTPUT_DIR) / f"short_drama_{title}_{timestamp}"
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # 3. 生成每个分镜
            total_shots = len(script.shots)
            shot_paths = []
            
            for idx, shot in enumerate(script.shots):
                if self.cancel_flag:
                    raise InterruptedError("用户取消")
                
                if cancel_callback and cancel_callback():
                    raise InterruptedError("用户取消")
                
                progress = 5 + (idx / total_shots) * 80
                if progress_callback:
                    progress_callback(progress, f"🎬 生成分镜 {idx+1}/{total_shots}: {shot.action[:30]}...")
                
                # 生成提示词
                prompt = self._build_shot_prompt(shot, script)
                
                # 生成视频片段 - 使用生成器
                try:
                    video_path = generator.generate(
                        prompt=prompt,
                        num_frames=settings.DEFAULT_NUM_FRAMES,
                        fps=settings.DEFAULT_FPS,
                        width=settings.DEFAULT_WIDTH,
                        height=settings.DEFAULT_HEIGHT,
                        guidance_scale=settings.DEFAULT_GUIDANCE_SCALE,
                        num_inference_steps=settings.DEFAULT_NUM_INFERENCE_STEPS,
                        progress_callback=lambda p, m: None,
                        cancel_callback=cancel_callback,
                        generation_id=f"{self._task_id}_shot_{idx+1}",
                    )
                    if video_path:
                        shot_paths.append(video_path)
                        self.generated_shots.append(video_path)
                except InterruptedError:
                    raise
                except Exception as e:
                    logger.warning(f"⚠️ 分镜 {idx+1} 生成失败: {e}")
                    continue
            
            if not shot_paths:
                raise ValueError("没有成功生成任何分镜")
            
            # 4. 拼接视频
            if progress_callback:
                progress_callback(90, "🎞️ 正在拼接视频...")
            
            final_path = self._compose_video(shot_paths, script)
            
            if progress_callback:
                progress_callback(100, "✅ 短剧生成完成！")
            
            logger.info(f"✅ 短剧生成完成: {final_path}")
            return final_path
            
        except InterruptedError:
            logger.info("⏹️ 短剧生成被取消")
            raise
        except Exception as e:
            logger.error(f"❌ 短剧生成失败: {e}")
            raise
        finally:
            self.is_generating = False
    
    def _build_shot_prompt(self, shot: Shot, script: Script) -> str:
        """构建分镜提示词"""
        parts = []
        
        parts.append("masterpiece, best quality, 8k, highly detailed")
        
        if shot.characters:
            char_desc = []
            for char_name in shot.characters:
                for char in script.characters:
                    if char.name == char_name:
                        if char.appearance:
                            char_desc.append(char.appearance)
                        if char.clothing:
                            char_desc.append(f"wearing {char.clothing}")
                        break
            if char_desc:
                parts.append(", ".join(char_desc))
        
        if shot.action:
            parts.append(shot.action)
        
        if shot.scene:
            parts.append(shot.scene)
        
        angle_map = {
            "close-up": "close-up shot, detailed face",
            "medium-shot": "medium shot, upper body visible",
            "wide-shot": "wide shot, full body visible",
        }
        parts.append(angle_map.get(shot.camera_angle, "medium shot"))
        
        if script.scenes and script.scenes[0].lighting:
            parts.append(script.scenes[0].lighting)
        
        return ", ".join(parts)
    
    def _compose_video(self, video_paths: List[Path], script: Script) -> Path:
        """拼接视频"""
        import subprocess
        
        output_path = self.output_dir / f"{script.title}_final.mp4"
        
        list_path = self.output_dir / "file_list.txt"
        with open(list_path, 'w', encoding='utf-8') as f:
            for path in video_paths:
                f.write(f"file '{path.resolve()}'\n")
        
        try:
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(list_path),
                '-c', 'copy',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.warning(f"FFmpeg 拼接警告: {result.stderr[:200]}")
                if video_paths:
                    return video_paths[0]
                return output_path
            
            logger.info(f"✅ 视频拼接完成: {output_path}")
            return output_path
            
        except Exception as e:
            logger.warning(f"视频拼接失败: {e}，返回第一个片段")
            return video_paths[0] if video_paths else output_path
    
    def cancel(self):
        """取消生成"""
        self.cancel_flag = True
        self.is_generating = False
        generator.cancel()


# 全局实例
short_drama_generator = ShortDramaGenerator()