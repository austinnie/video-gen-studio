import torch
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video
from accelerate import cpu_offload
import gc
from pathlib import Path
from config.settings import settings
from utils.logger import get_logger
from utils.memory import log_memory_usage

logger = get_logger(__name__)

class ModelLoader:
    """CogVideoX模型加载器 - 针对32GB内存CPU环境优化"""
    
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
        
        try:
            logger.info("正在加载 CogVideoX-2B 模型...")
            log_memory_usage()
            
            if progress_callback:
                progress_callback(10, "正在初始化模型...")
            
            # 加载模型 - 使用CPU和内存优化
            pipe = CogVideoXPipeline.from_pretrained(
                settings.MODEL_NAME,
                torch_dtype=torch.float32,  # CPU使用float32
                cache_dir=settings.MODEL_CACHE_DIR,
                low_cpu_mem_usage=True,
            )
            
            if progress_callback:
                progress_callback(40, "模型加载完成，正在优化...")
            
            # 关键：启用CPU Offload
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