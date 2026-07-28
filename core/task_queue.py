#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
任务队列 - 串行执行，支持取消
"""

import threading
import time
import gc
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
    args: tuple = ()
    kwargs: dict = None


class TaskQueue:
    """任务队列 - 单例模式，串行执行，支持取消"""
    
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
        
        logger.info("📋 任务队列已初始化")
    
    def add_task(self, name: str, func: Callable, args: tuple = None, kwargs: dict = None) -> Task:
        """添加任务到队列"""
        self._task_counter += 1
        task = Task(
            id=f"task_{self._task_counter:04d}",
            name=name,
            func=func,
            created_at=datetime.now().strftime("%H:%M:%S"),
            args=args or (),
            kwargs=kwargs or {},
        )
        
        self._queue.append(task)
        logger.info(f"📥 任务入队: {name} (ID: {task.id})")
        
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
        
        threading.Thread(target=self._run_next, daemon=True).start()
    
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
            
            result = task.func(*task.args, **task.kwargs)
            
            if task.status == TaskStatus.CANCELLED:
                logger.info(f"⏹️ 任务已取消: {task.name}")
                return
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().strftime("%H:%M:%S")
            task.result = result
            
            logger.info(f"✅ 任务完成: {task.name} (ID: {task.id})")
            
        except InterruptedError:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now().strftime("%H:%M:%S")
            task.error = "用户取消"
            logger.info(f"⏹️ 任务取消: {task.name}")
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now().strftime("%H:%M:%S")
            task.error = str(e)
            logger.error(f"❌ 任务失败: {task.name} - {e}")
        finally:
            self._current_task = None
            
            # 清理内存
            gc.collect()
            
            with self._lock:
                if self._queue:
                    threading.Thread(target=self._run_next, daemon=True).start()
                else:
                    self._is_running = False
    
    def cancel_current(self):
        """取消当前任务 - 完整取消"""
        logger.info("⏹️ 正在取消当前任务...")
        
        # 1. 取消生成器
        try:
            from core.generator import generator
            generator.cancel()
            logger.info("   ✅ 生成器已取消")
        except Exception as e:
            logger.warning(f"   ⚠️ 取消生成器失败: {e}")
        
        # 2. 取消短剧生成器
        try:
            from core.short_drama import short_drama_generator
            short_drama_generator.cancel()
            logger.info("   ✅ 短剧生成器已取消")
        except Exception as e:
            logger.warning(f"   ⚠️ 取消短剧生成器失败: {e}")
        
        # 3. 标记当前任务为取消
        if self._current_task:
            self._current_task.status = TaskStatus.CANCELLED
            self._current_task.error = "用户取消"
            logger.info(f"   ✅ 任务已标记取消: {self._current_task.name}")
            self._current_task = None
        
        # 4. 清空队列
        if self._queue:
            count = len(self._queue)
            self._queue.clear()
            logger.info(f"   ✅ 已清空 {count} 个等待任务")
        
        # 5. 重置运行状态
        self._is_running = False
        
        # 6. 清理内存
        gc.collect()
        logger.info("   🧹 内存已清理")
        
        logger.info("⏹️ 取消完成")
    
    def get_status(self) -> dict:
        """获取队列状态"""
        return {
            "queue_length": len(self._queue),
            "is_running": self._is_running,
            "current_task": {
                "name": self._current_task.name if self._current_task else None,
            } if self._current_task else None,
            "pending_tasks": [{"name": t.name, "id": t.id} for t in self._queue],
        }
    
    def clear(self):
        """清空队列"""
        count = len(self._queue)
        self._queue.clear()
        logger.info(f"🗑️ 队列已清空 ({count} 个任务)")
    
    def is_running(self) -> bool:
        """检查是否有任务在运行"""
        return self._is_running or self._current_task is not None


task_queue = TaskQueue()