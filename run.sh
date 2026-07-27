#!/bin/bash
echo "🎬 启动本地视频生成工作室..."
echo "注意: 首次运行将下载约5GB模型文件"
echo ""

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py