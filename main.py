#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from utils.logger import setup_logging, get_logger
from utils.memory import memory_monitor
from ui.app import main as app_main

logger = get_logger(__name__)


def main():
    setup_logging()
    
    # 创建目录
    Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("🎬 本地视频生成工作室")
    logger.info(f"   输出: {settings.OUTPUT_DIR}")
    logger.info("=" * 60)
    
    # ===== 启动内存监控 =====
    memory_monitor.start()
    
    # 启动 GUI
    app_main()


if __name__ == "__main__":
    main()