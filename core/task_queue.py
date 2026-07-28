#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
任务队列 - 串行执行，防止并发冲突
"""

import threading
import time
from typing import Callable, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from utils.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    """任务对象"""
    id: str
    name: str
    func: Callable
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    result: any = None
    error: str = ""
    progress: int = 0
    message: str = "等待执行"


class TaskQueue:
    """任务队列 - 单例模式，串行执行"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._queue: List[Task] = []
        self._is_running = False
        self._current_task: Optional[Task] = None
        self._task_counter = 0
        self._cancel_flag = False
        
        # 回调
        self._on_task_start = None
        self._on_task_progress = None
        self._on_task_complete = None
        
        logger.info("📋 任务队列已初始化")
    
    def add_task(self, name: str, func: Callable, args: tuple = None, kwargs: dict = None) -> Task:
        """
        添加任务到队列
        
        Args:
            name: 任务名称
            func: 执行函数
            args: 位置参数
            kwargs: 关键字参数
        
        Returns:
            Task: 任务对象
        """
        self._task_counter += 1
        task = Task(
            id=f"task_{self._task_counter:04d}",
            name=name,
            func=func,
            created_at=datetime.now().strftime("%H:%M:%S"),
        )
        
        task.args = args or ()
        task.kwargs = kwargs or {}
        
        self._queue.append(task)
        logger.info(f"📥 任务入队: {name} (ID: {task.id})")
        
        # 启动队列处理
        self._process_queue()
        
        return task
    
    def _process_queue(self):
        """处理队列"""
        with self._lock:
            if self._is_running:
                return
            if not self._queue:
                return
            
            self._is_running = True
        
        # 在后台线程执行
        import threading
        thread = threading.Thread(target=self._run_next, daemon=True)
        thread.start()
    
    def _run_next(self):
        """执行下一个任务"""
        with self._lock:
            if not self._queue:
                self._is_running = False
                return
            
            task = self._queue.pop(0)
            self._current_task = task
        
        try:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().strftime("%H:%M:%S")
            
            logger.info(f"▶️ 开始执行: {task.name} (ID: {task.id})")
            
            # 执行任务
            result = task.func(*task.args, **task.kwargs)
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().strftime("%H:%M:%S")
            task.result = result
            
            logger.info(f"✅ 任务完成: {task.name} (ID: {task.id})")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now().strftime("%H:%M:%S")
            task.error = str(e)
            logger.error(f"❌ 任务失败: {task.name} - {e}")
        
        finally:
            self._current_task = None
            
            # 执行下一个
            with self._lock:
                if self._queue:
                    import threading
                    threading.Thread(target=self._run_next, daemon=True).start()
                else:
                    self._is_running = False
    
    def cancel_current(self):
        """取消当前任务"""
        if self._current_task:
            self._current_task.status = TaskStatus.CANCELLED
            self._current_task.error = "用户取消"
            logger.info(f"⏹️ 任务已取消: {self._current_task.name}")
            self._current_task = None
    
    def get_status(self) -> dict:
        """获取队列状态"""
        return {
            "queue_length": len(self._queue),
            "is_running": self._is_running,
            "current_task": {
                "name": self._current_task.name if self._current_task else None,
                "progress": self._current_task.progress if self._current_task else 0,
                "message": self._current_task.message if self._current_task else "",
            } if self._current_task else None,
            "pending_tasks": [{"name": t.name, "id": t.id} for t in self._queue],
        }
    
    def clear(self):
        """清空队列"""
        self._queue.clear()
        logger.info("🗑️ 队列已清空")


# ============================================================
# 全局实例
# ============================================================

task_queue = TaskQueue()


# ============================================================
# 装饰器：自动入队
# ============================================================

def queue_task(name: str):
    """装饰器：将函数作为任务加入队列"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            task = task_queue.add_task(name, func, args, kwargs)
            return task
        return wrapper
    return decorator