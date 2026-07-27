import subprocess
import shutil
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

def post_process_video(
    video_path: Path,
    prompt: str = "",
    add_watermark: bool = False,
    compress: bool = True,
    target_bitrate: str = "2M",
) -> Path:
    """
    视频后处理：压缩、添加水印等
    
    Args:
        video_path: 原始视频路径
        prompt: 提示词（用于元数据）
        add_watermark: 是否添加水印
        compress: 是否压缩
        target_bitrate: 目标码率
    
    Returns:
        处理后的视频路径
    """
    # 检查ffmpeg是否可用
    if not shutil.which('ffmpeg'):
        logger.warning("ffmpeg未安装，跳过视频后处理")
        return video_path
    
    if not compress:
        return video_path
    
    output_path = video_path.parent / f"{video_path.stem}_processed.mp4"
    
    try:
        cmd = [
            'ffmpeg', '-y',  # -y 覆盖已有文件
            '-i', str(video_path),
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-b:v', target_bitrate,
            '-maxrate', target_bitrate,
            '-bufsize', '4M',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            str(output_path)
        ]
        
        logger.info(f"🎞️ 压缩视频: {video_path.name}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and output_path.exists():
            # 删除原始文件，替换为压缩版本
            video_path.unlink()
            output_path.rename(video_path)
            logger.info(f"✅ 视频已压缩: {video_path}")
            return video_path
        else:
            logger.warning(f"压缩失败: {result.stderr[:200]}")
            return video_path
            
    except Exception as e:
        logger.warning(f"视频后处理失败: {e}")
        return video_path

def get_video_info(video_path: Path) -> dict:
    """获取视频信息"""
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', str(video_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            streams = data.get('streams', [])
            video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
            if video_stream:
                return {
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'duration': float(video_stream.get('duration', 0)),
                    'fps': eval(video_stream.get('r_frame_rate', '0/0'))[0] if '/' in video_stream.get('r_frame_rate', '0/0') else 0,
                }
        return {}
    except Exception as e:
        logger.warning(f"获取视频信息失败: {e}")
        return {}