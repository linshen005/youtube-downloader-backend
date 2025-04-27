import os
import time
import logging
import shutil
from typing import List, Optional

logger = logging.getLogger(__name__)

def clean_old_files(directory: str, max_age_hours: int = 24) -> List[str]:
    """
    清理指定目录中的旧文件
    
    Args:
        directory: 目录路径
        max_age_hours: 文件最大保留时间（小时）
        
    Returns:
        被删除的文件列表
    """
    if not os.path.exists(directory) or not os.path.isdir(directory):
        logger.warning(f"Directory does not exist: {directory}")
        return []
    
    deleted_files = []
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if not os.path.isfile(file_path):
                continue
                
            file_age = current_time - os.path.getmtime(file_path)
            if file_age > max_age_seconds:
                try:
                    os.remove(file_path)
                    deleted_files.append(filename)
                    logger.info(f"Deleted old file: {filename}")
                except Exception as e:
                    logger.error(f"Failed to delete file {filename}: {str(e)}")
    except Exception as e:
        logger.error(f"Error while cleaning old files: {str(e)}")
    
    return deleted_files

def ensure_directory(directory: str) -> bool:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
        
    Returns:
        操作是否成功
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {directory}: {str(e)}")
        return False

def format_size(size_bytes: int) -> str:
    """
    格式化文件大小显示
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        格式化后的文件大小字符串
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    
    size_kb = size_bytes / 1024
    if size_kb < 1024:
        return f"{size_kb:.2f} KB"
    
    size_mb = size_kb / 1024
    if size_mb < 1024:
        return f"{size_mb:.2f} MB"
    
    size_gb = size_mb / 1024
    return f"{size_gb:.2f} GB"

def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除不合法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # 替换不合法的文件名字符
    illegal_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    
    # 限制文件名长度
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200] + ext
    
    return filename

def detect_platform(url: str) -> str:
    """
    检测URL所属的平台
    
    Args:
        url: 视频URL
        
    Returns:
        平台名称，如YouTube, Bilibili等
    """
    url = url.lower()
    
    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"
    elif "bilibili.com" in url:
        return "Bilibili"
    elif "tiktok.com" in url:
        return "TikTok"
    elif "twitter.com" in url or "x.com" in url:
        return "Twitter"
    elif "facebook.com" in url or "fb.com" in url:
        return "Facebook"
    elif "instagram.com" in url:
        return "Instagram"
    
    return "Unknown" 