from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
import os
import yt_dlp
import logging
import uuid
import time
from datetime import datetime
import shutil

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建下载目录
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 创建FastAPI应用
app = FastAPI(
    title="Video Downloader API",
    description="API for downloading videos from various platforms",
    version="1.0.0",
)

# 添加CORS中间件，允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该指定确切的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 下载进度跟踪
download_progress: Dict[str, Dict[str, Any]] = {}

# 请求模型
class DownloadRequest(BaseModel):
    url: str
    format: str = "mp4"  # mp4 或 mp3

# 检查ffmpeg是否可用
def check_ffmpeg():
    import subprocess
    try:
        result = subprocess.run(['which', 'ffmpeg'], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

FFMPEG_AVAILABLE = check_ffmpeg()

# 进度钩子
def progress_hook(d):
    download_id = d.get('info_dict', {}).get('__download_id')
    if not download_id:
        return
    
    if d['status'] == 'downloading':
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
        downloaded_bytes = d.get('downloaded_bytes', 0)
        
        if total_bytes > 0:
            percent = (downloaded_bytes / total_bytes) * 100
            download_progress[download_id].update({
                'status': 'downloading',
                'percent': f"{percent:.1f}%",
                'downloaded': downloaded_bytes,
                'total': total_bytes,
                'speed': d.get('speed', 0),
                'eta': d.get('eta', 0),
                'filename': d.get('filename', ''),
            })
    
    elif d['status'] == 'finished':
        download_progress[download_id].update({
            'status': 'processing',
            'percent': '100%',
            'message': '处理中...' if download_progress[download_id].get('language') == 'zh' else 'Processing...'
        })
    
    elif d['status'] == 'error':
        download_progress[download_id].update({
            'status': 'error',
            'message': d.get('error', '下载出错') if download_progress[download_id].get('language') == 'zh' else d.get('error', 'Download error')
        })

# 清理旧文件（作为后台任务）
def cleanup_old_files(max_age_hours=24):
    try:
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for filename in os.listdir(DOWNLOAD_DIR):
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.isfile(file_path):
                file_age = now - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    logger.info(f"Removed old file: {filename}")
    except Exception as e:
        logger.error(f"Error cleaning up old files: {e}")

@app.on_event("startup")
async def startup_event():
    cleanup_old_files()  # 启动时清理旧文件

@app.get("/")
async def read_root():
    return {"message": "Video Downloader API is running"}

@app.post("/api/download")
async def download_video(request: DownloadRequest, background_tasks: BackgroundTasks):
    url = request.url
    format_choice = request.format
    language = "en"  # 默认语言，可以通过请求头获取
    
    if not url:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "URL is required"}
        )
    
    # 生成唯一下载ID
    download_id = str(uuid.uuid4())
    
    # 初始化进度信息
    download_progress[download_id] = {
        'status': 'starting',
        'percent': '0%',
        'message': '准备下载...' if language == 'zh' else 'Preparing download...',
        'language': language
    }
    
    try:
        # 创建临时目录用于此次下载
        temp_dir = os.path.join(DOWNLOAD_DIR, download_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # 配置yt-dlp选项
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
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
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "message": "FFmpeg not installed. Cannot convert to MP3."
                    }
                )
        else:  # mp4
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
            })
        
        # 后台下载视频
        background_tasks.add_task(download_in_background, url, ydl_opts, download_id, format_choice)
        
        return {"success": True, "download_id": download_id}
    
    except Exception as e:
        logger.error(f"Error starting download: {str(e)}")
        if download_id in download_progress:
            download_progress[download_id]['status'] = 'error'
            download_progress[download_id]['message'] = str(e)
        
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error: {str(e)}"}
        )

async def download_in_background(url, ydl_opts, download_id, format_choice):
    try:
        # 先获取视频信息
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video')
        
        # 下载视频
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # 找到下载的文件
        temp_dir = os.path.join(DOWNLOAD_DIR, download_id)
        downloaded_files = os.listdir(temp_dir)
        
        if not downloaded_files:
            download_progress[download_id].update({
                'status': 'error',
                'message': '下载完成但未找到文件' if download_progress[download_id].get('language') == 'zh' else 'Download completed but no file found'
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
        final_file_path = os.path.join(DOWNLOAD_DIR, final_filename)
        
        # 移动文件
        shutil.move(original_file_path, final_file_path)
        
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # 获取文件大小
        file_size = os.path.getsize(final_file_path)
        size_mb = file_size / (1024 * 1024)
        
        # 更新进度信息
        download_progress[download_id].update({
            'status': 'completed',
            'percent': '100%',
            'message': '下载完成' if download_progress[download_id].get('language') == 'zh' else 'Download complete',
            'file': {
                'name': final_filename,
                'path': final_file_path,
                'size': f"{size_mb:.2f} MB",
                'url': f"/api/download/{final_filename}"
            }
        })
        
    except Exception as e:
        logger.error(f"Error during download: {str(e)}")
        download_progress[download_id].update({
            'status': 'error',
            'message': str(e)
        })

@app.get("/api/progress/{download_id}")
async def get_progress(download_id: str):
    if download_id in download_progress:
        return download_progress[download_id]
    return {"status": "not_found", "message": "Download not found"}

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path, 
        filename=filename,
        media_type='application/octet-stream'
    )

@app.get("/api/files")
async def list_files():
    files = []
    for filename in os.listdir(DOWNLOAD_DIR):
        if os.path.isfile(os.path.join(DOWNLOAD_DIR, filename)):
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            file_size = os.path.getsize(file_path)
            size_mb = file_size / (1024 * 1024)
            
            # 获取文件修改时间
            modified_time = os.path.getmtime(file_path)
            modified_date = datetime.fromtimestamp(modified_time).strftime('%Y-%m-%d %H:%M:%S')
            
            files.append({
                'name': filename,
                'size': f"{size_mb:.2f} MB",
                'date': modified_date,
                'url': f"/api/download/{filename}"
            })
    
    # 按修改时间降序排序
    files.sort(key=lambda x: x['date'], reverse=True)
    return files

@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    file_path = os.path.join(DOWNLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        os.remove(file_path)
        return {"success": True, "message": "File deleted"}
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 