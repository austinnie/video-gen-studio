from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional

@dataclass
class ModelConfig:
    """单个模型配置"""
    choice: str           # 模型标识，如 "zeroscope"
    name: str             # 显示名称
    hf_id: str            # Hugging Face ID
    ms_id: str            # ModelScope ID
    size: str             # 模型大小
    local_dir: str        # 本地目录名
    description: str      # 简短描述
    
    # 生成参数推荐值
    default_frames: int = 30
    default_fps: int = 8
    default_width: int = 576
    default_height: int = 320
    default_guidance_scale: float = 7.5
    default_steps: int = 50

@dataclass
class Settings:
    BASE_DIR: Path = Path(__file__).parent.parent

    # ===== 所有可用模型列表 =====
    AVAILABLE_MODELS: List[ModelConfig] = field(default_factory=lambda: [
        ModelConfig(
            choice="zeroscope",
            name="Zeroscope v2",
            hf_id="cerspense/zeroscope_v2_576w",
            ms_id="cerspense/zeroscope_v2_576w",
            size="~1.7GB",
            local_dir="zeroscope",
            description="轻量快速 · 推荐日常使用",
            default_frames=30,
            default_fps=8,
            default_width=576,
            default_height=320,
            default_guidance_scale=7.5,
            default_steps=50,
        ),
        ModelConfig(
            choice="text-to-video",
            name="Text-to-Video (阿里)",
            hf_id="damo-vilab/text-to-video-ms-1.7b",
            ms_id="damo-vilab/text-to-video-ms-1.7b",
            size="~1.7GB (仅safetensors)",
            local_dir="text-to-video",
            description="阿里达摩院开源",
            default_frames=16,
            default_fps=8,
            default_width=256,
            default_height=256,
            default_guidance_scale=9.0,
            default_steps=30,
        ),
        ModelConfig(
            choice="cogvideox-2b",
            name="CogVideoX-2B",
            hf_id="THUDM/CogVideoX-2b",
            ms_id="ZhipuAI/CogVideoX-2b",
            size="~5-6GB",
            local_dir="ZhipuAI/CogVideoX-2b",
            description="清华开源 · 质量好 · 需申请权限",
            default_frames=49,
            default_fps=8,
            default_width=576,
            default_height=320,
            default_guidance_scale=6.0,
            default_steps=50,
        ),
    ])

    # ===== 当前选中的模型 =====
    _current_choice: str = "zeroscope"

    @property
    def MODEL_CHOICE(self) -> str:
        return self._current_choice

    @MODEL_CHOICE.setter
    def MODEL_CHOICE(self, value: str):
        self._current_choice = value

    @property
    def current_model(self) -> Optional[ModelConfig]:
        """获取当前模型配置"""
        for m in self.AVAILABLE_MODELS:
            if m.choice == self._current_choice:
                return m
        return self.AVAILABLE_MODELS[0] if self.AVAILABLE_MODELS else None

    @property
    def MODEL_PATH(self) -> str:
        """当前模型本地路径"""
        m = self.current_model
        return str(self.BASE_DIR / "models" / m.local_dir) if m else ""

    @property
    def MODEL_NAME(self) -> str:
        """当前模型 HF ID"""
        m = self.current_model
        return m.hf_id if m else ""

    @property
    def DEFAULT_PROMPT(self) -> str:
        return "A serene landscape with mountains and a river flowing through a valley, sunset lighting, 8k, highly detailed"

    @property
    def DEFAULT_NEGATIVE_PROMPT(self) -> str:
        return "worst quality, low quality, blurry, distorted, deformed, ugly, bad anatomy"

    # ===== 当前模型的推荐参数 =====
    @property
    def DEFAULT_NUM_FRAMES(self) -> int:
        m = self.current_model
        return m.default_frames if m else 30

    @property
    def DEFAULT_FPS(self) -> int:
        m = self.current_model
        return m.default_fps if m else 8

    @property
    def DEFAULT_WIDTH(self) -> int:
        m = self.current_model
        return m.default_width if m else 576

    @property
    def DEFAULT_HEIGHT(self) -> int:
        m = self.current_model
        return m.default_height if m else 320

    @property
    def DEFAULT_GUIDANCE_SCALE(self) -> float:
        m = self.current_model
        return m.default_guidance_scale if m else 7.5

    @property
    def DEFAULT_NUM_INFERENCE_STEPS(self) -> int:
        m = self.current_model
        return m.default_steps if m else 50

    # ===== 其他配置 =====
    DEVICE: str = "cpu"
    ENABLE_CPU_OFFLOAD: bool = True
    OUTPUT_DIR: str = str(BASE_DIR / "outputs")
    MEMORY_WARNING_THRESHOLD: float = 4.0

    def get_model_by_choice(self, choice: str) -> Optional[ModelConfig]:
        for m in self.AVAILABLE_MODELS:
            if m.choice == choice:
                return m
        return None

    def get_model_names(self) -> List[str]:
        """获取所有模型的显示名称列表（用于UI下拉框）"""
        return [f"{m.name} ({m.size})" for m in self.AVAILABLE_MODELS]

    def get_choice_by_display(self, display: str) -> Optional[str]:
        """根据显示名称获取模型标识"""
        for m in self.AVAILABLE_MODELS:
            if f"{m.name} ({m.size})" == display:
                return m.choice
        return None


settings = Settings()

# 打印当前配置
print(f"📦 当前模型: {settings.current_model.name if settings.current_model else 'None'}")
print(f"📁 模型路径: {settings.MODEL_PATH}")