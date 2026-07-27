import torch
from diffusers import CogVideoXPipeline
import gc
from pathlib import Path

from config.settings import settings
from utils.logger import get_logger
from utils.memory import log_memory_usage

logger = get_logger(__name__)


class ModelLoader:
    """CogVideoX模型加载器 - 使用本地模型"""
    
    _instance = None
    _pipeline = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_model(self, progress_callback=None):
        """加载模型（支持进度回调）"""
        if self._pipeline is not None:
            logger.info("模型已加载，复用现有实例")
            return self._pipeline
        
        # 检查模型路径是否存在
        model_path = Path(settings.MODEL_PATH)
        if not model_path.exists():
            logger.error(f"❌ 模型路径不存在: {model_path}")
            logger.info("💡 请先运行: python scripts/download_model.py")
            raise FileNotFoundError(f"模型不存在: {model_path}")
        
        try:
            logger.info("正在加载 CogVideoX-2B 模型...")
            logger.info(f"   路径: {model_path}")
            log_memory_usage()
            
            if progress_callback:
                progress_callback(10, "正在初始化模型...")
            
            # 从本地加载模型
            pipe = CogVideoXPipeline.from_pretrained(
                str(model_path),
                torch_dtype=torch.float32,
                low_cpu_mem_usage=True,
            )
            
            if progress_callback:
                progress_callback(40, "模型加载完成，正在优化...")
            
            # 启用CPU Offload
            if settings.ENABLE_CPU_OFFLOAD:
                logger.info("启用 CPU Offload 优化...")
                pipe.enable_model_cpu_offload()
            
            # 启用VAE优化
            if settings.ENABLE_VAE_SLICING:
                pipe.vae.enable_slicing()
            if settings.ENABLE_VAE_TILING:
                pipe.vae.enable_tiling()
            
            # 内存优化
            pipe.text_encoder.to("cpu")
            pipe.transformer.to("cpu")
            
            self._pipeline = pipe
            log_memory_usage()
            
            if progress_callback:
                progress_callback(100, "模型就绪！")
            
            logger.info("✅ CogVideoX 模型加载完成")
            return pipe
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise RuntimeError(f"模型加载失败: {e}")
    
    def unload_model(self):
        """卸载模型释放内存"""
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
            gc.collect()
            logger.info("模型已卸载，内存已释放")
            log_memory_usage()
    
    def is_loaded(self) -> bool:
        return self._pipeline is not None


# 全局单例
model_loader = ModelLoader()