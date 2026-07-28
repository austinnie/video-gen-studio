#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
剧本处理器 - 将小说文本拆解为分镜脚本
"""

import json
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import requests

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Character:
    name: str
    gender: str = "unknown"
    age: str = "adult"
    ethnicity: str = "asian"
    appearance: str = ""
    personality: str = ""
    clothing: str = "casual"


@dataclass
class Scene:
    location: str = ""
    time: str = "day"
    lighting: str = "natural"
    atmosphere: str = "calm"


@dataclass
class Shot:
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
    title: str = "未命名"
    characters: List[Character] = field(default_factory=list)
    scenes: List[Scene] = field(default_factory=list)
    shots: List[Shot] = field(default_factory=list)
    raw_text: str = ""


class ScriptProcessor:
    """剧本处理器 - 使用 LLM 将小说拆解为分镜脚本"""
    
    def __init__(self):
        self.llm_model = "qwen2.5:1.5b"
        self.llm_url = "http://localhost:11434/api/generate"
        self._init_llm()
    
    def _init_llm(self):
        """初始化 LLM - 直接调用 Ollama API"""
        try:
            # 测试 Ollama 是否可用
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                models = [m["name"] for m in response.json().get("models", [])]
                if self.llm_model in models:
                    logger.info(f"✅ LLM 已就绪: {self.llm_model}")
                    self.llm_available = True
                    return
            self.llm_available = False
            logger.warning("⚠️ LLM 不可用，将使用规则引擎")
        except Exception as e:
            logger.warning(f"⚠️ LLM 连接失败: {e}，将使用规则引擎")
            self.llm_available = False
    
    def _call_llm(self, prompt: str, timeout: int = 120) -> Optional[str]:
        """调用 Ollama API"""
        if not self.llm_available:
            return None
        
        try:
            response = requests.post(
                self.llm_url,
                json={
                    "model": self.llm_model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
                timeout=timeout
            )
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                logger.warning(f"LLM API 错误: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"LLM 调用失败: {e}")
            return None
    
    def process(self, text: str, title: str = "") -> Script:
        """将小说文本处理为分镜脚本"""
        logger.info(f"📝 开始处理剧本: {title or '未命名'}")
        
        # 优先使用 LLM
        if self.llm_available:
            try:
                script = self._process_with_llm(text, title)
                if script and script.shots:
                    logger.info(f"✅ LLM 处理完成: {len(script.shots)} 个分镜")
                    return script
            except Exception as e:
                logger.warning(f"LLM 处理失败: {e}，使用规则引擎")
        
        # 回退到规则引擎
        logger.info("⚠️ 使用规则引擎")
        return self._process_with_rules(text, title)
    
    def _process_with_llm(self, text: str, title: str) -> Optional[Script]:
        """使用 LLM 处理剧本"""
        prompt = f"""你是一个专业的影视编剧。请将以下小说拆解为视频分镜脚本。

【小说内容】
{text[:3000]}

【输出格式 - 只输出 JSON】
{{
    "title": "故事标题",
    "characters": [
        {{"name": "角色名", "gender": "male/female", "age": "adult/child/elderly", "appearance": "外貌", "clothing": "服装"}}
    ],
    "shots": [
        {{
            "shot_id": 1,
            "scene": "场景地点",
            "characters": ["角色名"],
            "action": "动作描述（简洁，20字以内）",
            "camera_angle": "close-up/medium-shot/wide-shot"
        }}
    ]
}}

要求：
1. 提取 2-5 个主要角色
2. 拆解为 5-15 个分镜
3. 每个分镜 action 描述简洁（20字以内）
4. 只输出 JSON，不要其他内容

请输出 JSON："""

        response = self._call_llm(prompt)
        if not response:
            return None
        
        # 提取 JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            logger.warning("无法解析 LLM 响应")
            return None
        
        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}")
            return None
        
        script = Script(title=data.get("title", title))
        
        for char_data in data.get("characters", []):
            script.characters.append(Character(
                name=char_data.get("name", ""),
                gender=char_data.get("gender", "unknown"),
                age=char_data.get("age", "adult"),
                appearance=char_data.get("appearance", ""),
                clothing=char_data.get("clothing", "casual"),
            ))
        
        for shot_data in data.get("shots", []):
            script.shots.append(Shot(
                shot_id=shot_data.get("shot_id", len(script.shots) + 1),
                scene=shot_data.get("scene", ""),
                characters=shot_data.get("characters", []),
                action=shot_data.get("action", ""),
                dialogue=shot_data.get("dialogue", ""),
                camera_angle=shot_data.get("camera_angle", "medium-shot"),
            ))
        
        return script
    
    def _process_with_rules(self, text: str, title: str) -> Script:
        """使用规则引擎处理 (备用)"""
        script = Script(title=title or "未命名", raw_text=text)
        
        # 简单分割
        sentences = [s.strip() for s in re.split(r'[。！？.!?]', text) if len(s.strip()) > 5]
        
        # 提取角色
        char_names = self._extract_characters(text)
        for name in char_names[:5]:
            script.characters.append(Character(name=name))
        
        # 生成分镜
        for i, sentence in enumerate(sentences[:15], 1):
            script.shots.append(Shot(
                shot_id=i,
                scene=sentence[:30],
                characters=char_names[:2],
                action=sentence[:50],
                camera_angle="medium-shot",
            ))
        
        return script
    
    def _extract_characters(self, text: str) -> List[str]:
        from collections import Counter
        pattern = r'([\u4e00-\u9fa5]{2,4})'
        names = re.findall(pattern, text)
        counter = Counter(names)
        return [name for name, _ in counter.most_common(10)]


# 全局实例
script_processor = ScriptProcessor()