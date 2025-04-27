from fastapi import FastAPI, Form, HTTPException, Query, Path, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import asyncio
from typing import Optional
import re
from pathlib import Path as PathLib

# 导入下载函数
from download import download_audio, download_video
from utils import sanitize_filename, is_safe_filename, clean_old_files, schedule_file_cleanup

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Video Downloader API",
    description="API for downloading videos from YouTube",
    version="1.0.0",
)

# 添加CORS支持，允许前端访问API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有请求头
)

# Railway服务器基本URL
BASE_URL = "https://youtube-downloader-backend-production.up.railway.app"

# 下载目录路径
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 定时清理任务
cleanup_task = None

@app.on_event("startup")
async def startup_event():
    """应用启动时执行的事件"""
    global cleanup_task
    # 启动定时清理任务
    cleanup_task = asyncio.create_task(
        schedule_file_cleanup(DOWNLOAD_DIR, interval_minutes=10, max_age_minutes=30)
    )
    logger.info("已启动文件清理定时任务")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行的事件"""
    global cleanup_task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        logger.info("已取消文件清理定时任务")

@app.get("/")
async def read_root():
    """API根路径，返回基本信息"""
    return {
        "message": "Video Downloader API is running",
        "endpoints": {
            "download": "/download/",
            "download_file": "/download/file/{filename}"
        }
    }

@app.post("/download/")
async def download_content(url: str = Form(...), format: str = Form(...), mode: str = Query("direct")):
    """
    下载视频或音频
    
    Args:
        url: 视频链接
        format: 下载格式，'mp3'或'mp4'
        mode: 响应模式，'direct'直接返回文件，'json'返回JSON对象
    
    Returns:
        下载的文件或包含文件URL的JSON
    """
    # 验证输入参数
    if not url:
        return JSONResponse(
            status_code=400,
            content={"error": "URL不能为空"}
        )
    
    if format not in ["mp3", "mp4"]:
        return JSONResponse(
            status_code=400,
            content={"error": "格式必须是'mp3'或'mp4'"}
        )
    
    try:
        # 根据格式选择下载函数
        if format == "mp3":
            file_path = download_audio(url)
        else:  # mp4
            file_path = download_video(url)
        
        # 获取文件名
        filename = os.path.basename(file_path)
        
        # 根据模式返回不同响应
        if mode == "json":
            # 构建完整的文件URL，使用Railway服务器基本URL
            file_url = f"{BASE_URL}/download/file/{filename}"
            return JSONResponse(
                content={
                    "success": True,
                    "message": "下载成功",
                    "file": {
                        "url": file_url,
                        "name": filename
                    }
                }
            )
        else:  # direct模式
            # 直接返回文件
            return FileResponse(
                path=file_path,
                filename=filename,
                media_type='application/octet-stream'
            )
    
    except Exception as e:
        logger.error(f"下载失败: {str(e)}")
        # 返回错误信息
        return JSONResponse(
            status_code=500,
            content={"error": f"下载失败: {str(e)}"}
        )

@app.get("/download/file/{filename}")
async def get_file(filename: str = Path(..., title="文件名")):
    """
    获取已下载的文件
    
    Args:
        filename: 文件名
        
    Returns:
        文件响应
    """
    # 安全检查：防止路径穿越攻击
    if not is_safe_filename(filename):
        raise HTTPException(status_code=400, detail="无效的文件名")
    
    # 使用Path对象确保路径安全
    file_path_obj = PathLib(DOWNLOAD_DIR) / filename
    
    # 检查文件是否在downloads目录下
    if not str(file_path_obj.resolve()).startswith(str(PathLib(DOWNLOAD_DIR).resolve())):
        raise HTTPException(status_code=403, detail="Access denied")
    
    file_path = str(file_path_obj)
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

@app.get("/cleanup")
async def trigger_cleanup(minutes: int = Query(30, title="Minutes", description="文件最大保留时间（分钟）")):
    """
    手动触发清理过期文件（仅用于测试和管理）
    
    Args:
        minutes: 文件最大保留时间（分钟）
        
    Returns:
        清理结果
    """
    deleted = clean_old_files(DOWNLOAD_DIR, max_age_minutes=minutes)
    return {
        "success": True,
        "deleted_count": len(deleted),
        "deleted_files": deleted
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)