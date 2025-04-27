# 使用官方轻量版Python镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 拷贝依赖列表并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✨新增：安装ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# 再拷贝所有代码
COPY . .

# ✨默认启动命令
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]