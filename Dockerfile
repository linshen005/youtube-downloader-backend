# 使用完整的 Debian+Python 镜像，保证ffmpeg可以正常安装
FROM python:3.9-slim

# 安装ffmpeg并验证安装
RUN apt-get update && \
    apt-get install -y ffmpeg gcc && \
    ffmpeg -version && \
    which ffmpeg && \
    mkdir -p /app/bin && \
    ln -s $(which ffmpeg) /app/bin/ffmpeg && \
    ln -s $(which ffprobe) /app/bin/ffprobe

# 设置工作目录
WORKDIR /app

# 复制所有项目文件
COPY . /app/

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 添加环境变量，指定ffmpeg位置
ENV PATH="/app/bin:${PATH}"
ENV FFMPEG_LOCATION="/app/bin/ffmpeg"

# 开放端口
EXPOSE 8000

# 通过sh -c绑定动态端口
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]