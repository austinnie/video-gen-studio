#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
收集 universal_generator 目录下所有文件内容
用于分享给 AI 诊断问题
自动检测当前目录，无需硬编码
"""

import os
import sys
from pathlib import Path  # ✅ 添加这行
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 要排除的目录
EXCLUDE_DIRS = ["__pycache__", "outputs", ".git", "venv", "dist", "build", ".pytest_cache"]

# 要收集的文件扩展名
INCLUDE_EXTENSIONS = [".py", ".json", ".txt", ".md", ".yaml", ".yml"]

# 要排除的文件名模式
EXCLUDE_FILES = ["collect_files.py", "environment_report_*.txt", "*.pyc", "*.pyo"]


def get_target_directory():
    """
    自动获取目标目录
    优先级：命令行参数 > 脚本所在目录
    """
    # 如果有命令行参数，使用命令行参数
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        target = sys.argv[1]
        if os.path.exists(target):
            return target
        else:
            print(f"⚠️ 命令行指定的目录不存在: {target}")
    
    # 自动检测：从当前脚本所在目录向上查找
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 检查当前目录是否包含项目特征文件
    markers = ["main.py", "gui_config.json", "scene_patterns.json", "gui", "core"]
    current_dir = script_dir
    
    for marker in markers:
        if os.path.exists(os.path.join(current_dir, marker)):
            return current_dir
    
    # 如果当前目录没有，尝试父目录
    parent_dir = os.path.dirname(script_dir)
    for marker in markers:
        if os.path.exists(os.path.join(parent_dir, marker)):
            return parent_dir
    
    # 如果都找不到，提示用户输入
    print("⚠️ 无法自动检测项目目录")
    print("请确保脚本放在项目根目录下运行")
    print("或使用 --dir 参数指定目录")
    sys.exit(1)


def should_include_file(filepath):
    """判断是否应该包含该文件"""
    filename = os.path.basename(filepath)
    
    # 排除特定文件
    for pattern in EXCLUDE_FILES:
        if pattern.endswith("*"):
            if filename.startswith(pattern[:-1]):
                return False
        elif pattern.startswith("*") and filename.endswith(pattern[1:]):
            return False
        elif filename == pattern:
            return False
    
    # 检查扩展名
    ext = os.path.splitext(filename)[1].lower()
    return ext in INCLUDE_EXTENSIONS


def should_include_dir(dirpath):
    """判断是否应该包含该目录"""
    dirname = os.path.basename(dirpath)
    return dirname not in EXCLUDE_DIRS


def collect_files(directory):
    """收集目录下所有文件"""
    files = []
    
    for root, dirs, filenames in os.walk(directory):
        # 过滤排除的目录
        dirs[:] = [d for d in dirs if should_include_dir(os.path.join(root, d))]
        
        for filename in filenames:
            filepath = os.path.join(root, filename)
            if should_include_file(filepath):
                files.append(filepath)
    
    return sorted(files)


def read_file_content(filepath):
    """读取文件内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='gbk') as f:
                return f.read()
        except Exception as e:
            return f"[无法读取: {e}]"
    except Exception as e:
        return f"[读取错误: {e}]"


def generate_report(target_dir, output_file=None):
    """生成收集报告"""
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"project_snapshot_{timestamp}.txt"
    
    print(f"📂 收集目录: {target_dir}")
    print(f"📄 输出文件: {output_file}")
    print("=" * 70)
    
    files = collect_files(target_dir)
    print(f"✅ 找到 {len(files)} 个文件")
    
    with open(output_file, 'w', encoding='utf-8') as out:
        # 写入头部信息
        out.write("=" * 80 + "\n")
        out.write("Project Snapshot - 项目快照\n")
        out.write(f"收集时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        out.write(f"源目录: {target_dir}\n")
        out.write(f"文件总数: {len(files)}\n")
        out.write("=" * 80 + "\n\n")
        
        # 写入目录结构
        out.write("📁 目录结构:\n")
        out.write("-" * 40 + "\n")
        
        # 生成目录树
        for root, dirs, filenames in os.walk(target_dir):
            # 过滤排除的目录
            dirs[:] = [d for d in dirs if should_include_dir(os.path.join(root, d))]
            
            level = root.replace(target_dir, '').count(os.sep)
            indent = '│   ' * level
            if level > 0:
                out.write(f"{indent}├── {os.path.basename(root)}/\n")
            
            sub_indent = '│   ' * (level + 1)
            # 过滤并排序文件
            valid_files = [f for f in filenames if should_include_file(os.path.join(root, f))]
            for i, filename in enumerate(sorted(valid_files)):
                is_last = (i == len(valid_files) - 1)
                prefix = "└── " if is_last else "├── "
                out.write(f"{sub_indent}{prefix}{filename}\n")
        
        out.write("\n" + "=" * 80 + "\n")
        out.write("📄 文件内容:\n")
        out.write("=" * 80 + "\n\n")
        
        # 写入每个文件的内容
        for filepath in files:
            rel_path = os.path.relpath(filepath, target_dir)
            content = read_file_content(filepath)
            
            out.write("\n" + "=" * 80 + "\n")
            out.write(f"📄 文件: {rel_path}\n")
            out.write(f"路径: {filepath}\n")
            out.write("=" * 80 + "\n\n")
            out.write(content)
            out.write("\n\n")
    
    print(f"\n✅ 报告已生成: {output_file}")
    
    # 打印统计信息
    print("\n📊 统计信息:")
    print(f"   总文件数: {len(files)}")
    
    py_files = [f for f in files if f.endswith('.py')]
    json_files = [f for f in files if f.endswith('.json')]
    print(f"   Python 文件: {len(py_files)}")
    print(f"   JSON 文件: {len(json_files)}")
    
    # 打印文件列表（只显示前20个，避免太长）
    print("\n📋 文件列表（前20个）:")
    for f in files[:20]:
        rel_path = os.path.relpath(f, target_dir)
        size = os.path.getsize(f)
        print(f"   - {rel_path} ({size} bytes)")
    if len(files) > 20:
        print(f"   ... 共 {len(files)} 个文件")
    
    return output_file


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="收集项目目录下所有文件")
    parser.add_argument("--output", "-o", type=str, default=None,
                       help="输出文件路径")
    parser.add_argument("--dir", "-d", type=str, default=None,
                       help="要收集的目录（默认自动检测）")
    
    args = parser.parse_args()
    
    # 确定要收集的目录
    if args.dir:
        target_dir = args.dir
        if not os.path.exists(target_dir):
            print(f"❌ 目录不存在: {target_dir}")
            sys.exit(1)
    else:
        target_dir = get_target_directory()
    
    generate_report(target_dir, args.output)


if __name__ == "__main__":
    main()