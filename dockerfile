# 使用微软官方的 Playwright Python 镜像，自带 Chromium 及其所有系统底层依赖
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# 设置工作目录
WORKDIR /app

# 设置环境变量，防止 Python 生成 .pyc 文件，并设置无缓冲输出
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# 将 backend 和 data-pipeline 加入 Python 路径
ENV PYTHONPATH=/app/backend:/app/data-pipeline

# 复制依赖文件并安装（为了利用 Docker 缓存，先单独 Copy 这一个文件）
# 请确保你的根目录下有 requirements.txt
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 复制整个项目代码到容器中
COPY . /app/

# 暴露 FastAPI 的默认端口
EXPOSE 8000

# 启动 FastAPI 服务（请确认主程序的具体路径，这里假设是 backend.app.main:app）
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]