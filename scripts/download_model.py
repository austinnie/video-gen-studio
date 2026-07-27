#!/usr/bin/env python
"""模型下载脚本 - 支持 Hugging Face 和 ModelScope"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================
# 模型配置 - 可在此切换不同模型和源
# ============================================================

# 模型选择: "cogvideox-2b" 或 "text-to-video"
MODEL_CHOICE = "cogvideox-2b"

# Hugging Face 模型配置
HF_MODELS = {
    "cogvideox-2b": "THUDM/CogVideoX-2b",
    "cogvideox-1b": "THUDM/CogVideoX-1b",
    "text-to-video": "damo-vilab/text-to-video-ms-1.7b",
}

# ModelScope 模型配置 (国内源)
MODELSCOPE_MODELS = {
    "cogvideox-2b": "ZhipuAI/CogVideoX-2b",
    "text-to-video": "damo-vilab/text-to-video-ms-1.7b",
}

# 默认使用 ModelScope
USE_MODELSCOPE = True

# ============================================================

def get_model_id():
    if USE_MODELSCOPE:
        return MODELSCOPE_MODELS.get(MODEL_CHOICE, MODELSCOPE_MODELS["cogvideox-2b"])
    else:
        return HF_MODELS.get(MODEL_CHOICE, HF_MODELS["cogvideox-2b"])

def download_from_modelscope(model_id: str, cache_dir: str):
    """从 ModelScope 下载模型"""
    try:
        from modelscope.hub.snapshot_download import snapshot_download
        
        print(f"📦 正在从 ModelScope 下载...")
        print(f"   模型: {model_id}")
        print(f"   目录: {cache_dir}")
        
        # 移除 resume_download 参数（新版本已弃用）
        snapshot_download(
            model_id=model_id,
            cache_dir=cache_dir,
        )
        return True
    except ImportError:
        print("❌ modelscope 未安装，请运行: pip install modelscope")
        return False
    except Exception as e:
        print(f"❌ ModelScope 下载失败: {e}")
        return False

def download_from_huggingface(model_id: str, cache_dir: str):
    """从 Hugging Face 下载模型"""
    try:
        from huggingface_hub import snapshot_download
        
        print(f"📦 正在从 Hugging Face 下载...")
        print(f"   模型: {model_id}")
        print(f"   目录: {cache_dir}")
        
        # 尝试镜像
        for endpoint in [None, "https://hf-mirror.com"]:
            try:
                snapshot_download(
                    repo_id=model_id,
                    local_dir=cache_dir,
                    local_dir_use_symlinks=False,
                    resume_download=True,
                    endpoint=endpoint,
                )
                print(f"✅ 下载成功!")
                return True
            except Exception as e:
                if endpoint:
                    print(f"   ⚠️ 镜像失败: {e}")
                continue
        
        return False
    except ImportError:
        print("❌ huggingface_hub 未安装")
        return False
    except Exception as e:
        print(f"❌ Hugging Face 下载失败: {e}")
        return False

def download_from_modelscope_direct(model_id: str, cache_dir: str):
    """使用 modelscope 的 snapshot_download（兼容所有版本）"""
    try:
        import modelscope
        from modelscope.hub.snapshot_download import snapshot_download
        
        print(f"📦 正在从 ModelScope 下载 (兼容模式)...")
        print(f"   模型: {model_id}")
        print(f"   目录: {cache_dir}")
        
        # 兼容所有版本的调用方式
        try:
            snapshot_download(
                model_id=model_id,
                cache_dir=cache_dir,
                resume_download=True,
            )
        except TypeError:
            # 如果 resume_download 参数不支持，去掉它
            snapshot_download(
                model_id=model_id,
                cache_dir=cache_dir,
            )
        return True
    except ImportError:
        print("❌ modelscope 未安装")
        return False
    except Exception as e:
        print(f"❌ ModelScope 下载失败: {e}")
        return False

def update_config(model_id: str):
    """更新配置文件中的模型名称"""
    config_path = Path(__file__).parent.parent / "config" / "settings.py"
    
    if not config_path.exists():
        print(f"⚠️ 配置文件不存在: {config_path}")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        import re
        new_content = re.sub(
            r'MODEL_NAME: str = "[^"]+"',
            f'MODEL_NAME: str = "{model_id}"',
            content
        )
        
        if new_content != content:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ 配置文件已更新: MODEL_NAME = {model_id}")
            return True
    except Exception as e:
        print(f"⚠️ 配置文件更新失败: {e}")
        return False

def get_model_size(model_choice: str) -> str:
    sizes = {
        "cogvideox-2b": "~5-6GB",
        "cogvideox-1b": "~1.7GB",
        "text-to-video": "~1-2GB",
    }
    return sizes.get(model_choice, "未知")

def download_model():
    """主下载函数"""
    model_id = get_model_id()
    cache_dir = str(Path(__file__).parent.parent / "models")
    
    print("=" * 60)
    print("📦 模型下载工具")
    print(f"   选择: {MODEL_CHOICE}")
    print(f"   模型: {model_id}")
    print(f"   缓存: {cache_dir}")
    print(f"   大小: {get_model_size(MODEL_CHOICE)}")
    print(f"   源: {'ModelScope (国内)' if USE_MODELSCOPE else 'Hugging Face'}")
    print("=" * 60)
    print()
    
    os.makedirs(cache_dir, exist_ok=True)
    
    # 更新配置
    update_config(model_id)
    print()
    
    # 下载
    success = False
    
    if USE_MODELSCOPE:
        # 先尝试兼容模式
        success = download_from_modelscope_direct(model_id, cache_dir)
        if not success:
            print()
            print("🔄 尝试标准 ModelScope 方式...")
            success = download_from_modelscope(model_id, cache_dir)
        if not success:
            print()
            print("🔄 尝试 Hugging Face...")
            success = download_from_huggingface(model_id, cache_dir)
    else:
        success = download_from_huggingface(model_id, cache_dir)
        if not success:
            print()
            print("🔄 尝试 ModelScope...")
            success = download_from_modelscope_direct(model_id, cache_dir)
    
    if success:
        print()
        print("=" * 60)
        print("✅ 模型下载完成!")
        print(f"   目录: {cache_dir}")
        print("=" * 60)
        print()
        print("🚀 启动应用: python main.py")
    else:
        print()
        print("=" * 60)
        print("❌ 所有下载方式均失败")
        print("=" * 60)
        print()
        print("💡 手动下载方案:")
        print(f"   1. 访问: https://huggingface.co/{model_id}")
        print("   2. 申请访问权限（如需要）")
        print(f"   3. 将所有文件下载到: {cache_dir}")
        print()
        print("   ModelScope 备选 (安装后运行):")
        print("      pip install modelscope")
        print(f"      python -c \"from modelscope.hub.snapshot_download import snapshot_download; snapshot_download(model_id='{model_id}', cache_dir='{cache_dir}')\"")
        print()
        print("   或使用更轻量的公开模型:")
        print("      python scripts/download_model.py --model text-to-video")
        sys.exit(1)

if __name__ == "__main__":
    # 可选：接受命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--hf":
            USE_MODELSCOPE = False
            print("📌 使用 Hugging Face 源")
        elif sys.argv[1] == "--modelscope":
            USE_MODELSCOPE = True
            print("📌 使用 ModelScope 源")
        elif sys.argv[1] == "--model":
            if len(sys.argv) > 2:
                MODEL_CHOICE = sys.argv[2]
                print(f"📌 选择模型: {MODEL_CHOICE}")
    
    download_model()