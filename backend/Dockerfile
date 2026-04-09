# 使用官方 Playwright 镜像支持爬虫
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app

# 生产环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend:/app/data-pipeline
ENV TZ=Asia/Shanghai

# 强制系统时区，确保光伏测算时间准确
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 独立安装依赖利用缓存
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 将所有代码固化到镜像内部（生产环境严禁使用 Volume 覆盖代码）
COPY . /app/

EXPOSE 8000

# 生产启动命令：去掉 --reload
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]