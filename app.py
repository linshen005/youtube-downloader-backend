from fastapi import FastAPI, Form, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from typing import Optional

# 导入下载函数
from download import download_audio, download_video

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
    allow_origins=["*"],  # 在生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    """API根路径，返回基本信息"""
    return {
        "message": "Video Downloader API is running",
        "endpoints": {
            "download": "/download/"
        }
    }

@app.post("/download/")
async def download_content(url: str = Form(...), format: str = Form(...), mode: str = Query("direct")):
    """
    下载视频或音频
    
    Args:
        url: YouTube视频链接
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
            # 构建文件URL（在实际部署时需要替换为真实的域名和路径）
            file_url = f"/download/file/{filename}"
            return JSONResponse(
                content={
                    "success": True,
                    "message": "下载成功",
                    "file_url": file_url,
                    "file_name": filename
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
async def get_file(filename: str):
    """获取已下载的文件"""
    download_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
    file_path = os.path.join(download_dir, filename)
    
    if not os.path.exists(file_path):
        return JSONResponse(
            status_code=404,
            content={"error": "文件不存在"}
        )
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream'
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)