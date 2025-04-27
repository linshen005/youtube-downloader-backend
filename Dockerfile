# 使用轻量版Python镜像
FROM python:3.9-slim

# 安装ffmpeg和gcc
RUN apt-get update && apt-get install -y ffmpeg gcc

# 设置工作目录
WORKDIR /app

# 复制代码
COPY . /app/

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口
EXPOSE 8000

# 启动服务
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]