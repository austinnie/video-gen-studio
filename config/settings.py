import os
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Settings:
    BASE_DIR: Path = Path(__file__).parent.parent
    
    # ===== 模型配置 =====
    MODEL_CHOICE: str = "text-to-video"  # ✅ 改成 text-to-video
    MODEL_NAME: str = "damo-vilab/text-to-video-ms-1.7b"  # ✅ 改成这个
    MODEL_PATH: str = str(BASE_DIR / "models" / "text-to-video")  # ✅ 改成这个路径
    
    # 生成参数
    DEFAULT_NUM_FRAMES: int = 16   # text-to-video 建议 16 帧
    DEFAULT_FPS: int = 8
    DEFAULT_WIDTH: int = 256
    DEFAULT_HEIGHT: int = 256
    DEFAULT_GUIDANCE_SCALE: float = 9.0
    DEFAULT_NUM_INFERENCE_STEPS: int = 30
    
    # 硬件
    DEVICE: str = "cpu"
    ENABLE_CPU_OFFLOAD: bool = True
    ENABLE_VAE_SLICING: bool = True
    ENABLE_VAE_TILING: bool = True
    
    # 输出
    OUTPUT_DIR: str = str(BASE_DIR / "outputs")
    MAX_VIDEO_DURATION: int = 5
    
    # 内存阈值
    MEMORY_WARNING_THRESHOLD: float = 4.0

settings = Settings()

print(f"📦 模型类型: {settings.MODEL_CHOICE}")
print(f"📦 模型路径: {settings.MODEL_PATH}")
print(f"📁 路径存在: {os.path.exists(settings.MODEL_PATH)}")