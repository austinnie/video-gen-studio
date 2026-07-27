import psutil
import gc
import torch
from utils.logger import get_logger

logger = get_logger(__name__)

def get_memory_usage() -> dict:
    """获取当前内存使用情况"""
    try:
        process = psutil.Process()
        mem_info = process.memory_info()
        
        # 系统内存
        vm = psutil.virtual_memory()
        
        return {
            "process_rss_gb": mem_info.rss / 1024 / 1024 / 1024,
            "process_vms_gb": mem_info.vms / 1024 / 1024 / 1024,
            "system_total_gb": vm.total / 1024 / 1024 / 1024,
            "system_available_gb": vm.available / 1024 / 1024 / 1024,
            "system_percent": vm.percent,
        }
    except Exception as e:
        logger.warning(f"内存检测失败: {e}")
        return {}

def log_memory_usage():
    """记录内存使用日志"""
    mem = get_memory_usage()
    if mem:
        logger.info(f"💾 内存: 进程 {mem.get('process_rss_gb', 0):.1f}GB / "
                   f"系统 {mem.get('system_available_gb', 0):.1f}GB 可用 "
                   f"({mem.get('system_percent', 0)}% 使用)")

def ensure_memory_available(threshold_gb: float) -> bool:
    """检查内存是否充足"""
    mem = get_memory_usage()
    if mem:
        available = mem.get('system_available_gb', 0)
        if available < threshold_gb:
            logger.warning(f"⚠️ 内存不足! 可用: {available:.1f}GB, 建议: {threshold_gb}GB")
            return False
    return True

def force_memory_cleanup():
    """强制内存清理"""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("🧹 内存已清理")
    log_memory_usage()