#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志工具 - 统一日志管理
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path


# 日志颜色 (Windows 兼容)
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'


# 级别颜色映射
LEVEL_COLORS = {
    'DEBUG': Colors.CYAN,
    'INFO': Colors.GREEN,
    'WARNING': Colors.YELLOW,
    'ERROR': Colors.RED,
    'CRITICAL': Colors.MAGENTA + Colors.BOLD,
}


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    def format(self, record):
        levelname = record.levelname
        color = LEVEL_COLORS.get(levelname, Colors.RESET)
        record.levelname = f"{color}{levelname}{Colors.RESET}"
        return super().format(record)


class PlainFormatter(logging.Formatter):
    """纯文本日志格式化器（用于文件）"""
    
    def format(self, record):
        return super().format(record)


# 全局配置
_log_dir = None
_log_file = None
_initialized = False


def setup_logging(
    log_dir: str = "./logs",
    log_file: str = None,
    level: str = "INFO",
    console: bool = True,
    file_output: bool = True,
    colored: bool = True
):
    """设置全局日志系统"""
    global _log_dir, _log_file, _initialized
    
    if _initialized:
        return
    
    # 创建日志目录
    _log_dir = Path(log_dir)
    _log_dir.mkdir(parents=True, exist_ok=True)
    
    # 设置日志文件名
    if log_file is None:
        log_file = f"app_{datetime.now().strftime('%Y%m%d')}.log"
    _log_file = _log_dir / log_file
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    # 清除已有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 控制台输出
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        if colored:
            console_handler.setFormatter(ColoredFormatter(
                '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
                datefmt='%H:%M:%S'
            ))
        else:
            console_handler.setFormatter(PlainFormatter(
                '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
                datefmt='%H:%M:%S'
            ))
        root_logger.addHandler(console_handler)
    
    # 文件输出
    if file_output:
        file_handler = logging.FileHandler(_log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(PlainFormatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        root_logger.addHandler(file_handler)
    
    _initialized = True
    
    # 输出初始化信息
    logger = get_logger("logger")
    logger.info(f"📁 日志目录: {_log_dir}")
    logger.info(f"📄 日志文件: {_log_file}")
    logger.info(f"📊 日志级别: {level}")


def get_logger(name: str = "app") -> logging.Logger:
    """获取日志器实例"""
    if not _initialized:
        setup_logging()
    
    return logging.getLogger(name)


def set_level(level: str):
    """动态设置日志级别"""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger = get_logger("logger")
    logger.info(f"📊 日志级别已切换为: {level}")


def get_log_file():
    """获取当前日志文件路径"""
    return _log_file


def get_log_dir():
    """获取当前日志目录"""
    return _log_dir


# ===== 便捷函数 =====

def debug(msg: str, *args, **kwargs):
    get_logger().debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    get_logger().info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    get_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    get_logger().error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    get_logger().critical(msg, *args, **kwargs)


# ===== 兼容 print() 的包装函数 =====

def print_info(msg: str):
    info(msg)


def print_debug(msg: str):
    debug(msg)


def print_warning(msg: str):
    warning(msg)


def print_error(msg: str):
    error(msg)


# 自动初始化
setup_logging()