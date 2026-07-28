#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
剧本处理器 - 将小说文本拆解为分镜脚本
"""

import json
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Character:
    """角色定义"""
    name: str
    gender: str = "unknown"
    age: str = "adult"
    ethnicity: str = "asian"
    appearance: str = ""
    personality: str = ""
    clothing: str = "casual"


@dataclass
class Scene:
    """场景定义"""
    location: str = ""
    time: str = "day"
    lighting: str = "natural"
    atmosphere: str = "calm"


@dataclass
class Shot:
    """单个分镜"""
    shot_id: int
    scene: str
    characters: List[str]
    action: str
    dialogue: str = ""
    prompt: str = ""
    duration_seconds: int = 4
    camera_angle: str = "medium shot"


@dataclass
class Script:
    """完整剧本"""
    title: str = "未命名"
    characters: List[Character] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)
    shots: List[Shot] = field(default_factory=list)
    raw_text: str = ""


class ScriptProcessor:
    """剧本处理器 - 使用 LLM 将小说拆解为分镜脚本"""
    
    def __init__(self):
        self.llm = None
        self._init_llm()
    
    def _init_llm(self):
        """初始化 LLM"""
        try:
            from services.llm_service import llm_service
            self.llm = llm_service
        except ImportError:
            logger.warning("LLM 服务不可用，将使用规则引擎")
            self.llm = None
    
    def process(self, text: str, title: str = "") -> Script:
        """
        将小说文本处理为分镜脚本
        
        Args:
            text: 小说文本
            title: 作品标题
        
        Returns:
            Script: 完整剧本对象
        """
        logger.info(f"📝 开始处理剧本: {title or '未命名'}")
        
        script = Script(title=title or "未命名", raw_text=text)
        
        # 方法1: 使用 LLM (推荐)
        if self.llm and self.llm.is_available():
            try:
                return self._process_with_llm(text, title)
            except Exception as e:
                logger.warning(f"LLM 处理失败: {e}，使用规则引擎")
        
        # 方法2: 规则引擎 (备用)
        return self._process_with_rules(text, title)
    
    def _process_with_llm(self, text: str, title: str) -> Script:
        """使用 LLM 处理剧本"""
        prompt = f"""
你是一个专业的影视编剧。请将以下小说/故事拆解为视频分镜脚本。

【小说内容】
{text[:3000]}

【输出格式 - JSON】
{{
    "title": "故事标题",
    "characters": [
        {{"name": "角色名", "gender": "male/female", "age": "adult/child/elderly", "appearance": "外貌描述", "clothing": "服装"}}
    ],
    "scenes": [
        {{"location": "地点", "time": "day/night", "lighting": "bright/soft/dramatic", "atmosphere": "calm/intense/romantic"}}
    ],
    "shots": [
        {{
            "shot_id": 1,
            "scene": "场景描述",
            "characters": ["角色1", "角色2"],
            "action": "动作描述",
            "dialogue": "对话内容(可选)",
            "camera_angle": "close-up/medium-shot/wide-shot"
        }}
    ]
}}

要求：
1. 提取 2-5 个主要角色
2. 拆解为 5-15 个分镜
3. 每个分镜 3-5 秒
4. 用中文输出
5. 只输出 JSON，不要其他内容

请输出 JSON：
"""
        
        response = self.llm.generate(prompt, timeout=60, max_tokens=2000)
        
        if not response:
            raise ValueError("LLM 无响应")
        
        # 提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            raise ValueError("无法解析 LLM 响应")
        
        data = json.loads(json_match.group())
        
        # 构建 Script 对象
        script = Script(title=data.get("title", title))
        
        # 解析角色
        for char_data in data.get("characters", []):
            script.characters.append(Character(
                name=char_data.get("name", ""),
                gender=char_data.get("gender", "unknown"),
                age=char_data.get("age", "adult"),
                appearance=char_data.get("appearance", ""),
                clothing=char_data.get("clothing", "casual"),
            ))
        
        # 解析场景
        for scene_data in data.get("scenes", []):
            script.scenes.append(Scene(
                location=scene_data.get("location", ""),
                time=scene_data.get("time", "day"),
                lighting=scene_data.get("lighting", "natural"),
                atmosphere=scene_data.get("atmosphere", "calm"),
            ))
        
        # 解析分镜
        for shot_data in data.get("shots", []):
            script.shots.append(Shot(
                shot_id=shot_data.get("shot_id", len(script.shots) + 1),
                scene=shot_data.get("scene", ""),
                characters=shot_data.get("characters", []),
                action=shot_data.get("action", ""),
                dialogue=shot_data.get("dialogue", ""),
                camera_angle=shot_data.get("camera_angle", "medium-shot"),
            ))
        
        logger.info(f"✅ 剧本处理完成: {len(script.characters)} 个角色, {len(script.shots)} 个分镜")
        return script
    
    def _process_with_rules(self, text: str, title: str) -> Script:
        """使用规则引擎处理剧本 (备用方案)"""
        script = Script(title=title or "未命名", raw_text=text)
        
        # 简单的句子分割
        sentences = [s.strip() for s in re.split(r'[。！？.!?]', text) if len(s.strip()) > 5]
        
        # 提取角色 (简单规则)
        char_names = self._extract_characters(text)
        for name in char_names[:5]:
            script.characters.append(Character(name=name))
        
        # 生成分镜
        for i, sentence in enumerate(sentences[:15], 1):
            script.shots.append(Shot(
                shot_id=i,
                scene=sentence[:50],
                characters=char_names[:2],
                action=sentence[:100],
                camera_angle="medium-shot",
            ))
        
        logger.info(f"⚠️ 规则引擎处理完成: {len(script.shots)} 个分镜")
        return script
    
    def _extract_characters(self, text: str) -> List[str]:
        """提取角色名 (简单规则)"""
        # 人名模式: 姓+名 (中文)
        pattern = r'([\u4e00-\u9fa5]{2,4})'
        names = re.findall(pattern, text)
        # 去重，按出现频率排序
        from collections import Counter
        counter = Counter(names)
        return [name for name, _ in counter.most_common(10)]


# 全局实例
script_processor = ScriptProcessor()