import yt_dlp
import os
import shutil
import time
import logging
import uuid
import subprocess
from typing import Dict, Any, Optional, Callable
from utils import sanitize_filename, detect_platform

logger = logging.getLogger(__name__)

# 检查ffmpeg是否可用
def check_ffmpeg() -> bool:
    """检查系统是否安装了ffmpeg"""
    import subprocess
    try:
        result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

# 全局变量，保存ffmpeg是否可用
FFMPEG_AVAILABLE = check_ffmpeg()

def download_audio(url: str) -> str:
    """
    使用yt-dlp把给定的链接下载并提取成MP3格式
    
    Args:
        url: 视频链接
        
    Returns:
        保存的文件路径
    """
    logger.info(f"开始下载音频: {url}")
    
    # 检测平台
    platform = detect_platform(url)
    logger.info(f"检测到平台: {platform}")
    
    # 创建下载目录
    download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        # 先获取视频信息
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', f"{platform} audio")
            
        # 清理标题作为文件名
        safe_title = sanitize_filename(title)
        logger.info(f"视频标题: {title}")
        logger.info(f"安全文件名: {safe_title}")
        
        # 生成随机UUID作为文件名前缀
        file_uuid = str(uuid.uuid4())[:8]
        output_template = os.path.join(download_dir, f"{file_uuid}_{safe_title}.%(ext)s")
        
        # 构建下载命令
        cmd = [
            "yt-dlp",
            "-x",
            "--audio-format", "mp3",
            "-o", output_template,
            url
        ]
        
        # 执行下载命令
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"下载命令失败: {result.stderr}")
            raise Exception(f"下载失败: {result.stderr}")
        
        # 找到下载的文件
        expected_path = os.path.join(download_dir, f"{file_uuid}_{safe_title}.mp3")
        
        if os.path.exists(expected_path):
            logger.info(f"文件保存成功：{expected_path}")
            return expected_path
        else:
            # 可能文件名不是预期的，查找目录中以UUID开头的文件
            for filename in os.listdir(download_dir):
                if filename.startswith(f"{file_uuid}_"):
                    file_path = os.path.join(download_dir, filename)
                    logger.info(f"文件保存成功：{file_path}")
                    return file_path
            
            # 如果没有找到文件，抛出异常
            raise FileNotFoundError(f"下载完成但未找到文件：{expected_path}")
    except Exception as e:
        logger.error(f"下载音频时出错: {str(e)}")
        raise

def download_video(url: str) -> str:
    """
    使用yt-dlp把给定的链接下载成MP4格式
    
    Args:
        url: 视频链接
        
    Returns:
        保存的文件路径
    """
    logger.info(f"开始下载视频: {url}")
    
    # 检测平台
    platform = detect_platform(url)
    logger.info(f"检测到平台: {platform}")
    
    # 创建下载目录
    download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
    os.makedirs(download_dir, exist_ok=True)
    
    try:
        # 先获取视频信息
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', f"{platform} video")
            
        # 清理标题作为文件名
        safe_title = sanitize_filename(title)
        logger.info(f"视频标题: {title}")
        logger.info(f"安全文件名: {safe_title}")
        
        # 生成随机UUID作为文件名前缀
        file_uuid = str(uuid.uuid4())[:8]
        output_template = os.path.join(download_dir, f"{file_uuid}_{safe_title}.%(ext)s")
        
        # 构建下载命令
        cmd = [
            "yt-dlp",
            "-f", "bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", output_template,
            url
        ]
        
        # 执行下载命令
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"下载命令失败: {result.stderr}")
            raise Exception(f"下载失败: {result.stderr}")
        
        # 找到下载的文件
        expected_path = os.path.join(download_dir, f"{file_uuid}_{safe_title}.mp4")
        
        if os.path.exists(expected_path):
            logger.info(f"文件保存成功：{expected_path}")
            return expected_path
        else:
            # 可能文件名不是预期的，查找目录中以UUID开头的文件
            for filename in os.listdir(download_dir):
                if filename.startswith(f"{file_uuid}_"):
                    file_path = os.path.join(download_dir, filename)
                    logger.info(f"文件保存成功：{file_path}")
                    return file_path
            
            # 如果没有找到文件，抛出异常
            raise FileNotFoundError(f"下载完成但未找到文件：{expected_path}")
    except Exception as e:
        logger.error(f"下载视频时出错: {str(e)}")
        raise

class VideoDownloader:
    """视频下载器类，封装下载逻辑"""
    
    def __init__(self, download_dir: str):
        """
        初始化下载器
        
        Args:
            download_dir: 下载文件保存目录
        """
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
        # 下载进度跟踪字典
        self.progress_data: Dict[str, Dict[str, Any]] = {}
    
    def get_progress(self, download_id: str) -> Dict[str, Any]:
        """获取指定下载任务的进度信息"""
        if download_id in self.progress_data:
            return self.progress_data[download_id]
        return {"status": "not_found", "message": "Download not found"}
    
    def progress_hook(self, d: Dict[str, Any]) -> None:
        """yt-dlp进度回调函数"""
        download_id = d.get('info_dict', {}).get('__download_id')
        if not download_id or download_id not in self.progress_data:
            return
        
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            
            if total_bytes > 0:
                percent = (downloaded_bytes / total_bytes) * 100
                self.progress_data[download_id].update({
                    'status': 'downloading',
                    'percent': f"{percent:.1f}%",
                    'downloaded': downloaded_bytes,
                    'total': total_bytes,
                    'speed': d.get('speed', 0),
                    'eta': d.get('eta', 0),
                    'filename': d.get('filename', ''),
                })
        
        elif d['status'] == 'finished':
            self.progress_data[download_id].update({
                'status': 'processing',
                'percent': '100%',
                'message': '处理中...' if self.progress_data[download_id].get('language') == 'zh' else 'Processing...'
            })
        
        elif d['status'] == 'error':
            self.progress_data[download_id].update({
                'status': 'error',
                'message': d.get('error', '下载出错') if self.progress_data[download_id].get('language') == 'zh' else d.get('error', 'Download error')
            })
    
    async def download_video(self, url: str, format_choice: str, download_id: str, language: str = "en") -> None:
        """
        下载视频（异步函数，用于后台任务）
        
        Args:
            url: 视频URL
            format_choice: 下载格式，'mp4'或'mp3'
            download_id: 下载ID，用于跟踪进度
            language: 语言代码，用于提示消息
        """
        try:
            # 初始化进度信息
            self.progress_data[download_id] = {
                'status': 'starting',
                'percent': '0%',
                'message': '准备下载...' if language == 'zh' else 'Preparing download...',
                'language': language
            }
            
            # 创建临时目录用于此次下载
            temp_dir = os.path.join(self.download_dir, download_id)
            os.makedirs(temp_dir, exist_ok=True)
            
            # 配置yt-dlp选项
            ydl_opts = {
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'progress_hooks': [self.progress_hook],
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
            }
            
            # 将下载ID添加到info_dict以便在progress_hook中使用
            ydl_opts['postprocessor_args'] = ['-threads', '4']
            ydl_opts.setdefault('info_dict', {})['__download_id'] = download_id
            
            # 根据格式选择下载选项
            if format_choice == 'mp3':
                if FFMPEG_AVAILABLE:
                    ydl_opts.update({
                        'format': 'bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                    })
                else:
                    self.progress_data[download_id].update({
                        'status': 'error',
                        'message': "FFmpeg not installed. Cannot convert to MP3." if language == "en" else "未安装FFmpeg，无法转换为MP3格式"
                    })
                    return
            else:  # mp4
                ydl_opts.update({
                    'format': 'bestvideo+bestaudio/best',
                    'merge_output_format': 'mp4',
                })
            
            # 开始下载过程
            try:
                # 先获取视频信息
                with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'video')
                
                # 下载视频
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                # 找到下载的文件
                downloaded_files = os.listdir(temp_dir)
                
                if not downloaded_files:
                    self.progress_data[download_id].update({
                        'status': 'error',
                        'message': '下载完成但未找到文件' if language == 'zh' else 'Download completed but no file found'
                    })
                    return
                
                # 移动文件到主下载目录并生成唯一文件名
                downloaded_file = downloaded_files[0]
                original_file_path = os.path.join(temp_dir, downloaded_file)
                
                # 构建最终文件名（时间戳_标题.扩展名）
                timestamp = int(time.time())
                file_name, file_ext = os.path.splitext(downloaded_file)
                if format_choice == 'mp3' and not file_ext.lower() == '.mp3':
                    file_ext = '.mp3'
                elif format_choice == 'mp4' and not file_ext.lower() == '.mp4':
                    file_ext = '.mp4'
                
                final_filename = f"{timestamp}_{file_name}{file_ext}"
                final_file_path = os.path.join(self.download_dir, final_filename)
                
                # 移动文件
                shutil.move(original_file_path, final_file_path)
                
                # 清理临时目录
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                # 获取文件大小
                file_size = os.path.getsize(final_file_path)
                size_mb = file_size / (1024 * 1024)
                
                # 更新进度信息
                self.progress_data[download_id].update({
                    'status': 'completed',
                    'percent': '100%',
                    'message': '下载完成' if language == 'zh' else 'Download complete',
                    'file': {
                        'name': final_filename,
                        'path': final_file_path,
                        'size': f"{size_mb:.2f} MB",
                        'url': f"/api/download/{final_filename}"
                    }
                })
                
            except Exception as e:
                logger.error(f"Error during download: {str(e)}")
                self.progress_data[download_id].update({
                    'status': 'error',
                    'message': str(e)
                })
                # 清理临时目录
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
        
        except Exception as e:
            logger.error(f"Error in download process: {str(e)}")
            if download_id in self.progress_data:
                self.progress_data[download_id].update({
                    'status': 'error',
                    'message': str(e)
                })
    
    def get_file_info(self, filename: str) -> Optional[Dict[str, str]]:
        """获取已下载文件的信息"""
        file_path = os.path.join(self.download_dir, filename)
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return None
            
        file_size = os.path.getsize(file_path)
        size_mb = file_size / (1024 * 1024)
        
        # 获取文件修改时间
        modified_time = os.path.getmtime(file_path)
        modified_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(modified_time))
        
        return {
            'name': filename,
            'path': file_path,
            'size': f"{size_mb:.2f} MB",
            'date': modified_date,
            'url': f"/api/download/{filename}"
        }
    
    def list_files(self) -> list:
        """列出所有下载的文件"""
        files = []
        for filename in os.listdir(self.download_dir):
            file_path = os.path.join(self.download_dir, filename)
            if os.path.isfile(file_path):
                file_info = self.get_file_info(filename)
                if file_info:
                    files.append(file_info)
        
        # 按修改时间降序排序
        files.sort(key=lambda x: x['date'], reverse=True)
        return files
    
    def delete_file(self, filename: str) -> bool:
        """删除指定的文件"""
        file_path = os.path.join(self.download_dir, filename)
        if not os.path.exists(file_path):
            return False
        
        try:
            os.remove(file_path)
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False 