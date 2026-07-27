#!/usr/bin/env python
"""模型下载脚本 - 独立版本，不依赖 config"""

import os
import sys
from pathlib import Path
from huggingface_hub import snapshot_download

# ============================================================
# 配置要下载的模型
# ============================================================

MODELS = {
    "zeroscope": {
        "repo_id": "cerspense/zeroscope_v2_576w",
        "size": "~1.7GB",
        "local_dir": "zeroscope",
        "allow_patterns": ["*.safetensors", "*.json", "*.txt", "*.md"],
        "ignore_patterns": ["*.bin", "*.fp16.*"],
    },
    "text-to-video": {
        "repo_id": "damo-vilab/text-to-video-ms-1.7b",
        "size": "~5-6GB",
        "local_dir": "text-to-video",
    },
    "cogvideox-2b": {
        "repo_id": "THUDM/CogVideoX-2b",
        "size": "~5-6GB",
        "local_dir": "ZhipuAI/CogVideoX-2b",
    },
}


def download_model(name: str):
    """下载指定模型"""
    if name not in MODELS:
        print(f"❌ 未知模型: {name}")
        print(f"可用模型: {', '.join(MODELS.keys())}")
        return False

    config = MODELS[name]
    repo_id = config["repo_id"]
    local_dir = Path(__file__).parent.parent / "models" / config["local_dir"]

    print("=" * 60)
    print(f"📦 下载模型: {name}")
    print(f"   Hugging Face ID: {repo_id}")
    print(f"   大小: {config['size']}")
    print(f"   目录: {local_dir}")
    print("=" * 60)

    os.makedirs(local_dir, exist_ok=True)

    try:
        kwargs = {
            "repo_id": repo_id,
            "local_dir": str(local_dir),
            "resume_download": True,
        }
        if "allow_patterns" in config:
            kwargs["allow_patterns"] = config["allow_patterns"]
        if "ignore_patterns" in config:
            kwargs["ignore_patterns"] = config["ignore_patterns"]

        snapshot_download(**kwargs)
        print(f"\n✅ {name} 下载完成!")
        print(f"   目录: {local_dir}")
        return True

    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("📦 模型下载工具")
        print("=" * 60)
        print("\n用法:")
        print("  python download_model_standalone.py <模型名称>")
        print("\n可用模型:")
        for name, config in MODELS.items():
            print(f"  {name}  ({config['size']})")
        print("\n示例:")
        print("  python download_model_standalone.py zeroscope")
        return

    name = sys.argv[1]
    download_model(name)


if __name__ == "__main__":
    main()