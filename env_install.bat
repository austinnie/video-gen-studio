@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo 正在安装依赖包...
python -m pip install --upgrade pip
pip install -r requirements.txt

pause