#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
项目打包脚本 - 自动打包整个项目
自动识别项目文件夹名，生成 文件夹名_时间戳.zip
"""

import os
import zipfile
from pathlib import Path  # ✅ 添加这行
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 要排除的目录（完全跳过）
EXCLUDE_DIRS = [
    "__pycache__",
    "venv",
    "env",
    ".git",
    "outputs",
    "output",
    "models",
    "loras",
    "logs",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    "*.egg-info",
    "cache",
]

# 要排除的文件扩展名
EXCLUDE_EXTENSIONS = [
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite3",
    ".log",
    ".zip",
    ".rar",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".pkl",
]

# ✅ 要打包的根目录文件扩展名
ROOT_FILE_EXTS = ['.py', '.json', '.txt', '.md', '.yml', '.yaml']


def should_exclude(name, is_dir=False):
    """判断是否应该排除"""
    if is_dir:
        for pattern in EXCLUDE_DIRS:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
    else:
        ext = os.path.splitext(name)[1].lower()
        if ext in EXCLUDE_EXTENSIONS:
            return True
    return False


def get_project_name():
    """获取项目文件夹名"""
    return os.path.basename(os.getcwd())


def pack_project():
    """打包整个项目"""
    project_name = get_project_name()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"{project_name}_{timestamp}.zip"
    
    print("=" * 70)
    print(f"📦 打包项目: {project_name}")
    print(f"📁 当前目录: {os.getcwd()}")
    print(f"📄 输出文件: {zip_filename}")
    print("=" * 70)
    
    file_count = 0
    dir_count = 0
    added_files = set()  # ✅ 记录已添加的文件，避免重复
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 处理根目录下的文件
        print("   📄 处理根目录文件:")
        for file in os.listdir("."):
            if os.path.isfile(file):
                if should_exclude(file, is_dir=False):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in ROOT_FILE_EXTS:
                    zipf.write(file, file)
                    added_files.add(file)
                    file_count += 1
                    print(f"      ✅ {file}")
        
        # 处理子目录
        print("   📁 处理子目录:")
        for root, dirs, files in os.walk("."):
            if root == ".":
                dirs[:] = [d for d in dirs if not should_exclude(d, is_dir=True)]
                continue
            
            dir_name = os.path.basename(root)
            if should_exclude(dir_name, is_dir=True):
                dirs[:] = []
                continue
            
            dir_count += 1
            
            for file in files:
                if should_exclude(file, is_dir=False):
                    continue
                
                file_path = os.path.join(root, file)
                arcname = os.path.join(root, file)
                
                # ✅ 检查是否已添加
                if arcname in added_files:
                    continue
                    
                zipf.write(file_path, arcname)
                added_files.add(arcname)
                file_count += 1
                print(f"      ✅ {file_path}")
    
    print("=" * 70)
    print(f"✅ 打包完成!")
    print(f"   📦 文件: {zip_filename}")
    print(f"   📊 大小: {os.path.getsize(zip_filename) / 1024 / 1024:.2f} MB")
    print(f"   📁 目录: {dir_count} 个")
    print(f"   📄 文件: {file_count} 个")
    print("=" * 70)
    
    return zip_filename


if __name__ == "__main__":
    try:
        pack_project()
    except KeyboardInterrupt:
        print("\n⏹️ 用户取消")
    except Exception as e:
        print(f"\n❌ 打包失败: {e}")
        import traceback
        traceback.print_exc()
        input("按 Enter 键退出...")