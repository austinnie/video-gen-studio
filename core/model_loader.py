import torch
from diffusers import DiffusionPipeline, DPMSolverMultistepScheduler
import gc
from pathlib import Path

from config.settings import settings
from utils.logger import get_logger
from utils.memory import log_memory_usage

logger = get_logger(__name__)


class ModelLoader:
    _instance = None
    _pipeline = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_model(self, progress_callback=None):
        if self._pipeline is not None:
            logger.info("模型已加载，复用现有实例")
            return self._pipeline

        model_path = Path(settings.MODEL_PATH)
        if not model_path.exists():
            logger.error(f"❌ 模型路径不存在: {model_path}")
            raise FileNotFoundError(f"模型不存在: {model_path}")

        try:
            model_choice = settings.MODEL_CHOICE
            logger.info("正在加载模型...")
            logger.info(f"   路径: {model_path}")
            logger.info(f"   类型: {model_choice}")
            log_memory_usage()

            if progress_callback:
                progress_callback(10, "正在初始化模型...")

            # ===== 强制 CPU 模式 =====
            # 确保没有 CUDA
            if torch.cuda.is_available():
                logger.warning("⚠️ CUDA 可用但强制使用 CPU")
            
            # 根据模型类型选择加载方式
            if model_choice == "zeroscope" or model_choice == "text-to-video":
                logger.info("   📦 使用 DiffusionPipeline")
                pipe = DiffusionPipeline.from_pretrained(
                    str(model_path),
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True,
                )
            else:
                # CogVideoX 系列
                from diffusers import CogVideoXPipeline
                logger.info("   📦 使用 CogVideoXPipeline")
                pipe = CogVideoXPipeline.from_pretrained(
                    str(model_path),
                    torch_dtype=torch.float32,
                    low_cpu_mem_usage=True,
                )

            if progress_callback:
                progress_callback(40, "模型加载完成，正在优化...")

            # ===== 强制 CPU =====
            pipe.to("cpu")
            logger.info("   ✅ 模型已移至 CPU")

            # 设置调度器
            if hasattr(pipe, 'scheduler'):
                try:
                    pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                        pipe.scheduler.config
                    )
                except:
                    pass

            # ===== 禁用 CPU Offload（避免 CUDA 依赖） =====
            # 只启用 VAE 切片和注意力切片
            if hasattr(pipe, 'vae'):
                try:
                    pipe.vae.enable_slicing()
                    logger.info("   ✅ VAE 切片已启用")
                except:
                    pass

            try:
                pipe.enable_attention_slicing()
                logger.info("   ✅ 注意力切片已启用")
            except:
                pass

            # 不启用 CPU Offload
            # if settings.ENABLE_CPU_OFFLOAD:
            #     pipe.enable_model_cpu_offload()

            self._pipeline = pipe
            log_memory_usage()

            if progress_callback:
                progress_callback(100, "模型就绪！")

            logger.info(f"✅ {model_choice} 模型加载完成 (CPU 模式)")
            return pipe

        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"模型加载失败: {e}")

    def unload_model(self):
        if self._pipeline is not None:
            del self._pipeline
            self._pipeline = None
            gc.collect()
            logger.info("模型已卸载")

    def is_loaded(self) -> bool:
        return self._pipeline is not None


model_loader = ModelLoader()