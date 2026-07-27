"""
内存管理模块 - 监控、清理、优化
"""

import psutil
import gc
import torch
import threading
import time
from typing import Optional, Callable
from dataclasses import dataclass, field

from utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# 内存阈值配置
# ============================================================

@dataclass
class MemoryConfig:
    """内存配置 - 可调整"""
    
    # 系统内存阈值
    system_warning_threshold_gb: float = 4.0   # 系统可用内存低于此值发出警告 (GB)
    system_critical_threshold_gb: float = 2.0  # 系统可用内存低于此值执行清理 (GB)
    
    # 进程内存阈值
    process_warning_threshold_gb: float = 12.0  # 进程内存使用超过此值发出警告 (GB)
    process_cleanup_threshold_gb: float = 16.0  # 进程内存使用超过此值执行清理 (GB)
    
    # 监控间隔
    monitor_interval_seconds: int = 30  # 内存检查间隔
    
    # 是否启用自动清理
    auto_cleanup_enabled: bool = True
    
    # 清理后是否触发 GC
    gc_after_cleanup: bool = True


# ============================================================
# 核心函数
# ============================================================

_config = MemoryConfig()


def get_config() -> MemoryConfig:
    """获取当前配置"""
    return _config


def update_config(**kwargs):
    """更新配置"""
    for key, value in kwargs.items():
        if hasattr(_config, key):
            setattr(_config, key, value)
            logger.info(f"📊 内存配置更新: {key} = {value}")


def get_memory_usage() -> dict:
    """获取当前内存使用情况"""
    try:
        process = psutil.Process()
        mem_info = process.memory_info()
        vm = psutil.virtual_memory()
        
        return {
            "process_rss_gb": mem_info.rss / 1024 / 1024 / 1024,
            "process_vms_gb": mem_info.vms / 1024 / 1024 / 1024,
            "system_total_gb": vm.total / 1024 / 1024 / 1024,
            "system_available_gb": vm.available / 1024 / 1024 / 1024,
            "system_used_gb": vm.used / 1024 / 1024 / 1024,
            "system_percent": vm.percent,
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.warning(f"内存检测失败: {e}")
        return {}


def log_memory_usage():
    """记录内存使用日志"""
    mem = get_memory_usage()
    if mem:
        logger.info(
            f"💾 进程 {mem.get('process_rss_gb', 0):.1f}GB | "
            f"系统 {mem.get('system_used_gb', 0):.1f}/{mem.get('system_total_gb', 0):.1f}GB "
            f"({mem.get('system_percent', 0)}%) "
            f"可用 {mem.get('system_available_gb', 0):.1f}GB"
        )


def force_memory_cleanup():
    """强制内存清理"""
    # 1. Python GC
    gc.collect()
    
    # 2. 多次 GC (分代回收)
    for _ in range(3):
        gc.collect()
    
    # 3. PyTorch CUDA 缓存清理
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
    
    logger.info("🧹 内存已清理")
    log_memory_usage()


def check_and_cleanup() -> dict:
    """
    检查内存状态，必要时自动清理
    
    Returns:
        {"action": "ok"|"warning"|"cleanup", "message": str}
    """
    mem = get_memory_usage()
    if not mem:
        return {"action": "unknown", "message": "无法获取内存信息"}
    
    result = {"action": "ok", "message": "内存状态正常"}
    actions = []
    
    # 1. 检查系统可用内存
    available = mem.get('system_available_gb', 0)
    if available < _config.system_critical_threshold_gb:
        result["action"] = "cleanup"
        actions.append(f"系统可用内存不足 ({available:.1f}GB < {_config.system_critical_threshold_gb:.1f}GB)")
    elif available < _config.system_warning_threshold_gb:
        result["action"] = "warning"
        actions.append(f"系统可用内存较低 ({available:.1f}GB < {_config.system_warning_threshold_gb:.1f}GB)")
    
    # 2. 检查进程内存
    process_mem = mem.get('process_rss_gb', 0)
    if process_mem > _config.process_cleanup_threshold_gb:
        result["action"] = "cleanup"
        actions.append(f"进程内存使用过高 ({process_mem:.1f}GB > {_config.process_cleanup_threshold_gb:.1f}GB)")
    elif process_mem > _config.process_warning_threshold_gb:
        if result["action"] != "cleanup":
            result["action"] = "warning"
        actions.append(f"进程内存使用较高 ({process_mem:.1f}GB > {_config.process_warning_threshold_gb:.1f}GB)")
    
    # 3. 执行清理
    if result["action"] == "cleanup" and _config.auto_cleanup_enabled:
        logger.warning(f"⚠️ 触发自动清理: {', '.join(actions)}")
        force_memory_cleanup()
        result["message"] = "已执行自动清理: " + ", ".join(actions)
    elif actions:
        result["message"] = "; ".join(actions)
    
    return result


def ensure_memory_available(threshold_gb: float = None) -> bool:
    """
    检查内存是否充足
    如果未指定阈值，使用配置中的值
    """
    if threshold_gb is None:
        threshold_gb = _config.system_warning_threshold_gb
    
    mem = get_memory_usage()
    if mem:
        available = mem.get('system_available_gb', 0)
        if available < threshold_gb:
            logger.warning(f"⚠️ 内存不足! 可用: {available:.1f}GB, 建议: {threshold_gb:.1f}GB")
            return False
    return True


# ============================================================
# 后台监控器
# ============================================================

class MemoryMonitor:
    """后台内存监控器（单例）"""
    
    _instance = None
    _running = False
    _thread: Optional[threading.Thread] = None
    _callbacks: list = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._callbacks = []
        self._last_log_time = 0
    
    def start(self):
        """启动后台监控"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"📊 内存监控已启动 (间隔: {_config.monitor_interval_seconds}s)")
        logger.info(f"📊 系统可用内存阈值: {_config.system_warning_threshold_gb:.1f}GB (警告) / {_config.system_critical_threshold_gb:.1f}GB (清理)")
        logger.info(f"📊 进程内存阈值: {_config.process_warning_threshold_gb:.1f}GB (警告) / {_config.process_cleanup_threshold_gb:.1f}GB (清理)")
    
    def stop(self):
        """停止监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("📊 内存监控已停止")
    
    def add_callback(self, callback: Callable[[dict], None]):
        """添加内存状态回调"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[dict], None]):
        """移除回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                # 检查并清理
                result = check_and_cleanup()
                
                # 记录日志（每 5 分钟记录一次）
                current_time = time.time()
                if current_time - self._last_log_time > 300:
                    log_memory_usage()
                    self._last_log_time = current_time
                
                # 回调
                mem = get_memory_usage()
                for cb in self._callbacks:
                    try:
                        cb(mem)
                    except:
                        pass
                
                time.sleep(_config.monitor_interval_seconds)
                
            except Exception as e:
                logger.warning(f"内存监控错误: {e}")
                time.sleep(_config.monitor_interval_seconds)
    
    def get_status(self) -> dict:
        """获取当前状态"""
        mem = get_memory_usage()
        return {
            "running": self._running,
            "config": {
                "system_warning_threshold_gb": _config.system_warning_threshold_gb,
                "system_critical_threshold_gb": _config.system_critical_threshold_gb,
                "process_warning_threshold_gb": _config.process_warning_threshold_gb,
                "process_cleanup_threshold_gb": _config.process_cleanup_threshold_gb,
                "monitor_interval": _config.monitor_interval_seconds,
                "auto_cleanup_enabled": _config.auto_cleanup_enabled,
            },
            "memory": mem,
        }


# ============================================================
# 上下文管理器
# ============================================================

class MemoryCleanupContext:
    """内存清理上下文管理器"""
    
    def __enter__(self):
        log_memory_usage()
        return self
    
    def __exit__(self, *args):
        force_memory_cleanup()


# ============================================================
# 装饰器
# ============================================================

def auto_cleanup(func):
    """自动清理装饰器"""
    def wrapper(*args, **kwargs):
        with MemoryCleanupContext():
            return func(*args, **kwargs)
    return wrapper


def memory_guard(func):
    """内存守卫装饰器 - 检查内存后执行"""
    def wrapper(*args, **kwargs):
        if not ensure_memory_available():
            logger.warning("⚠️ 内存不足，执行清理后重试...")
            force_memory_cleanup()
            if not ensure_memory_available():
                raise MemoryError("内存不足，无法执行")
        return func(*args, **kwargs)
    return wrapper


# ============================================================
# 全局实例
# ============================================================

memory_monitor = MemoryMonitor()


# ============================================================
# 便捷函数
# ============================================================

def get_available_memory_gb() -> float:
    """获取可用内存（GB）"""
    mem = get_memory_usage()
    return mem.get('system_available_gb', 0)


def get_process_memory_gb() -> float:
    """获取进程内存使用（GB）"""
    mem = get_memory_usage()
    return mem.get('process_rss_gb', 0)


def is_memory_low(threshold_gb: float = 4.0) -> bool:
    """检查内存是否不足"""
    return get_available_memory_gb() < threshold_gb