#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
短剧生成器 - 使用任务队列，支持取消
"""

import os
import time
import gc
from pathlib import Path
from typing import Optional, Callable, List
from datetime import datetime

from config.settings import settings
from core.script_processor import Script, Shot, script_processor
from core.generator import generator
from utils.logger import get_logger
from utils.memory import log_memory_usage

logger = get_logger(__name__)


class ShortDramaGenerator:
    """短剧生成器 - 支持取消"""
    
    def __init__(self):
        self.is_generating = False
        self.cancel_flag = False
        self.current_script = None
        self.generated_shots = []
        self.output_dir = None
        self._task_id = None
        self._current_shot_index = 0
    
    def generate_from_text(
        self,
        text: str,
        title: str = "",
        progress_callback: Optional[Callable] = None,
        cancel_callback: Optional[Callable] = None,
    ) -> Path:
        """从小说文本生成短剧"""
        self.is_generating = True
        self.cancel_flag = False
        self.generated_shots = []
        self._current_shot_index = 0
        
        try:
            # 1. 处理剧本
            if progress_callback:
                progress_callback(5, "📝 正在拆解剧本...")
            
            script = script_processor.process(text, title)
            self.current_script = script
            
            logger.info("=" * 60)
            logger.info(f"📋 剧本拆解完成: {len(script.shots)} 个分镜")
            logger.info("=" * 60)
            
            for i, shot in enumerate(script.shots, 1):
                logger.info(f"  [{i}] {shot.action} ({shot.camera_angle})")
                
            logger.info("=" * 60)
            
            if not script.shots:
                raise ValueError("剧本拆解失败，没有分镜")
            
            # 2. 创建输出目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_dir = Path(settings.OUTPUT_DIR) / f"short_drama_{title}_{timestamp}"
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 输出目录: {self.output_dir}")
            
            # 3. 生成每个分镜
            total_shots = len(script.shots)
            shot_paths = []
            
            for idx, shot in enumerate(script.shots):
                self._current_shot_index = idx + 1
                
                # 检查取消
                if self.cancel_flag:
                    raise InterruptedError("用户取消")
                if cancel_callback and cancel_callback():
                    self.cancel_flag = True
                    raise InterruptedError("用户取消")
                
                shot_num = idx + 1
                
                logger.info("-" * 50)
                logger.info(f"🎬 开始生成分镜 [{shot_num}/{total_shots}]")
                logger.info(f"   动作: {shot.action[:60]}...")
                logger.info("-" * 50)
                
                progress = 5 + (idx / total_shots) * 80
                if progress_callback:
                    progress_callback(progress, f"🎬 生成分镜 {shot_num}/{total_shots}")
                
                prompt = self._build_shot_prompt(shot, script)
                logger.info(f"   📝 提示词: {prompt}")
                
                try:
                    start_time = time.time()
                    logger.info(f"   ⏳ 开始生成...")
                    
                    video_path = generator.generate(
                        prompt=prompt,
                        num_frames=settings.DEFAULT_NUM_FRAMES,
                        fps=settings.DEFAULT_FPS,
                        width=settings.DEFAULT_WIDTH,
                        height=settings.DEFAULT_HEIGHT,
                        guidance_scale=settings.DEFAULT_GUIDANCE_SCALE,
                        num_inference_steps=settings.DEFAULT_NUM_INFERENCE_STEPS,
                        progress_callback=lambda p, m: None,
                        cancel_callback=lambda: self.cancel_flag,
                        generation_id=f"{self._task_id}_shot_{shot_num}",
                    )
                    
                    elapsed = time.time() - start_time
                    
                    if video_path:
                        shot_paths.append(video_path)
                        self.generated_shots.append(video_path)
                        logger.info(f"   ✅ 分镜 [{shot_num}/{total_shots}] 完成! 耗时: {elapsed/60:.1f} 分钟")
                        logger.info(f"   📁 保存: {video_path}")
                    else:
                        logger.warning(f"   ⚠️ 分镜 [{shot_num}/{total_shots}] 返回空路径")
                        
                except InterruptedError:
                    logger.info(f"   ⏹️ 分镜 [{shot_num}/{total_shots}] 被取消")
                    raise
                except Exception as e:
                    logger.error(f"   ❌ 分镜 [{shot_num}/{total_shots}] 生成失败: {e}")
                    continue
                
                # 每次分镜后清理内存
                gc.collect()
                log_memory_usage()
            
            logger.info("=" * 60)
            logger.info(f"📊 分镜生成统计:")
            logger.info(f"   ✅ 成功: {len(shot_paths)}/{total_shots}")
            logger.info(f"   ❌ 失败: {total_shots - len(shot_paths)}")
            logger.info("=" * 60)
            
            if not shot_paths:
                raise ValueError("没有成功生成任何分镜")
            
            # 4. 拼接视频
            if progress_callback:
                progress_callback(90, "🎞️ 正在拼接视频...")
            
            logger.info("🎞️ 开始拼接视频...")
            final_path = self._compose_video(shot_paths, script)
            
            if progress_callback:
                progress_callback(100, "✅ 短剧生成完成！")
            
            logger.info("=" * 60)
            logger.info(f"✅ 短剧生成完成!")
            logger.info(f"   📁 最终视频: {final_path}")
            logger.info("=" * 60)
            
            return final_path
            
        except InterruptedError:
            logger.info("⏹️ 短剧生成被取消")
            raise
        except Exception as e:
            logger.error(f"❌ 短剧生成失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            self.is_generating = False
            gc.collect()
    
    def _build_shot_prompt(self, shot: Shot, script: Script) -> str:
        """构建分镜提示词 - 精简版"""
        parts = []
        
        parts.append("masterpiece, best quality")
        
        if shot.characters:
            char_name = shot.characters[0]
            for char in script.characters:
                if char.name == char_name:
                    if char.appearance:
                        parts.append(char.appearance[:20])
                    if char.clothing:
                        parts.append(f"wearing {char.clothing[:15]}")
                    break
        
        if shot.action:
            # 提取英文词
            import re
            english_words = re.findall(r'[a-zA-Z]+', shot.action)
            if english_words:
                parts.append(" ".join(english_words[:8]))
        
        if shot.scene:
            import re
            scene_words = re.findall(r'[a-zA-Z]+', shot.scene)
            if scene_words:
                parts.append(" ".join(scene_words[:5]))
        
        angle_map = {
            "close-up": "close-up",
            "medium-shot": "medium shot",
            "wide-shot": "wide shot",
        }
        parts.append(angle_map.get(shot.camera_angle, "medium shot"))
        
        prompt = ", ".join(parts)
        
        if len(prompt) > 200:
            prompt = prompt[:200]
            last_comma = prompt.rfind(',')
            if last_comma > 100:
                prompt = prompt[:last_comma]
        
        return prompt
    
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
            
            logger.info(f"✅ 拼接完成: {output_path}")
            return output_path
            
        except Exception as e:
            logger.warning(f"视频拼接失败: {e}，返回第一个片段")
            return video_paths[0] if video_paths else output_path
    
    def cancel(self):
        """取消生成"""
        self.cancel_flag = True
        self.is_generating = False
        generator.cancel()
        logger.info("⏹️ 短剧生成器已取消")


# 全局实例
short_drama_generator = ShortDramaGenerator()