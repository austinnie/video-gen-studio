#!/usr/bin/env python
"""模型下载脚本 - 支持批量下载多个模型"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================
# 配置要下载的模型列表
# ============================================================

# 要下载的模型列表 (可以添加多个)
MODELS_TO_DOWNLOAD = [
    {
        "choice": "text-to-video",
        "hf_id": "damo-vilab/text-to-video-ms-1.7b",
        "ms_id": "damo-vilab/text-to-video-ms-1.7b",
        "size": "~1-2GB",
        "local_dir": "text-to-video",
    },
    {
        "choice": "cogvideox-2b",
        "hf_id": "THUDM/CogVideoX-2b",
        "ms_id": "ZhipuAI/CogVideoX-2b",
        "size": "~5-6GB",
        "local_dir": "ZhipuAI/CogVideoX-2b",
    },
    # 可以继续添加更多模型...
    # {
    #     "choice": "text-to-video",
    #     "hf_id": "damo-vilab/text-to-video-ms-1.7b",
    #     "ms_id": "damo-vilab/text-to-video-ms-1.7b",
    #     "size": "~1-2GB",
    #     "local_dir": "damo-vilab/text-to-video-ms-1.7b",
    # },
]

# 默认源: "modelscope" 或 "huggingface"
SOURCE = "modelscope"

# ============================================================

def download_from_modelscope(model_id: str, cache_dir: str):
    """从 ModelScope 下载模型"""
    try:
        from modelscope.hub.snapshot_download import snapshot_download
        
        print(f"📦 正在从 ModelScope 下载...")
        print(f"   模型: {model_id}")
        print(f"   目录: {cache_dir}")
        
        try:
            snapshot_download(
                model_id=model_id,
                cache_dir=cache_dir,
                resume_download=True,
            )
        except TypeError:
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

def download_from_huggingface(model_id: str, local_dir: str):
    """从 Hugging Face 下载模型"""
    try:
        from huggingface_hub import snapshot_download
        
        print(f"📦 正在从 Hugging Face 下载...")
        print(f"   模型: {model_id}")
        print(f"   目录: {local_dir}")
        
        for endpoint in [None, "https://hf-mirror.com"]:
            try:
                snapshot_download(
                    repo_id=model_id,
                    local_dir=local_dir,
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

def download_model(model_config):
    """下载单个模型"""
    choice = model_config["choice"]
    hf_id = model_config["hf_id"]
    ms_id = model_config["ms_id"]
    size = model_config["size"]
    local_dir = model_config["local_dir"]
    
    cache_dir = str(Path(__file__).parent.parent / "models" / local_dir)
    
    print()
    print("=" * 60)
    print(f"📦 下载模型: {choice}")
    print(f"   大小: {size}")
    print(f"   目录: {cache_dir}")
    print("=" * 60)
    
    os.makedirs(cache_dir, exist_ok=True)
    
    success = False
    
    if SOURCE == "modelscope":
        success = download_from_modelscope(ms_id, cache_dir)
        if not success:
            print("🔄 切换到 Hugging Face...")
            success = download_from_huggingface(hf_id, cache_dir)
    else:
        success = download_from_huggingface(hf_id, cache_dir)
        if not success:
            print("🔄 切换到 ModelScope...")
            success = download_from_modelscope(ms_id, cache_dir)
    
    return success

def download_all_models():
    """下载所有配置的模型"""
    print("=" * 60)
    print("📦 批量模型下载工具")
    print(f"   源: {SOURCE}")
    print(f"   模型数量: {len(MODELS_TO_DOWNLOAD)}")
    print("=" * 60)
    
    success_count = 0
    failed_models = []
    
    for i, model_config in enumerate(MODELS_TO_DOWNLOAD, 1):
        print(f"\n[{i}/{len(MODELS_TO_DOWNLOAD)}]")
        if download_model(model_config):
            success_count += 1
            print(f"✅ {model_config['choice']} 下载完成!")
        else:
            failed_models.append(model_config['choice'])
            print(f"❌ {model_config['choice']} 下载失败")
    
    print()
    print("=" * 60)
    print(f"📊 下载完成: 成功 {success_count}/{len(MODELS_TO_DOWNLOAD)}")
    if failed_models:
        print(f"❌ 失败的模型: {', '.join(failed_models)}")
    print("=" * 60)

def download_single_model(choice):
    """下载单个指定模型"""
    for model_config in MODELS_TO_DOWNLOAD:
        if model_config["choice"] == choice:
            download_model(model_config)
            return
    
    print(f"❌ 未找到模型: {choice}")
    print(f"可用模型: {', '.join([m['choice'] for m in MODELS_TO_DOWNLOAD])}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            print("可用模型:")
            for m in MODELS_TO_DOWNLOAD:
                print(f"  {m['choice']} ({m['size']})")
        elif sys.argv[1] == "--model":
            if len(sys.argv) > 2:
                download_single_model(sys.argv[2])
            else:
                print("请指定模型名称")
        elif sys.argv[1] == "--hf":
            SOURCE = "huggingface"
            print("📌 使用 Hugging Face 源")
            download_all_models()
        else:
            download_all_models()
    else:
        # 默认下载所有模型
        download_all_models()