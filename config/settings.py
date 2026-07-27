import os
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Settings:
    # 项目根目录
    BASE_DIR: Path = Path(__file__).parent.parent
    
    # 模型配置
    MODEL_NAME: str = "ZhipuAI/CogVideoX-2b"
    MODEL_CACHE_DIR: str = str(BASE_DIR / "models")
    
    # 生成参数默认值
    DEFAULT_NUM_FRAMES: int = 49      # CogVideoX-2B 支持49帧 (约4-6秒)
    DEFAULT_FPS: int = 8
    DEFAULT_WIDTH: int = 576
    DEFAULT_HEIGHT: int = 320
    DEFAULT_GUIDANCE_SCALE: float = 6.0
    DEFAULT_NUM_INFERENCE_STEPS: int = 50
    
    # 硬件配置
    DEVICE: str = "cpu"               # 强制使用CPU
    ENABLE_CPU_OFFLOAD: bool = True   # 关键：内存卸载
    ENABLE_VAE_SLICING: bool = True
    ENABLE_VAE_TILING: bool = True
    
    # 输出配置
    OUTPUT_DIR: str = str(BASE_DIR / "outputs")
    MAX_VIDEO_DURATION: int = 10      # 最大视频时长（秒）
    
    # 内存阈值
    MEMORY_WARNING_THRESHOLD: float = 28.0  # GB

settings = Settings()