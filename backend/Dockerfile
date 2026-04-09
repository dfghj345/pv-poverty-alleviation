FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

WORKDIR /app/backend

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
ARG PIP_DEFAULT_TIMEOUT=180
ARG PIP_RETRIES=10

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST} \
    PIP_DEFAULT_TIMEOUT=${PIP_DEFAULT_TIMEOUT} \
    PIP_RETRIES=${PIP_RETRIES} \
    PYTHONPATH=/app/backend:/app \
    TZ=Asia/Shanghai

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY requirements.txt /app/requirements.txt
RUN python -c "import playwright" \
    && grep -vEi '^[[:space:]]*playwright([[:space:]=<>!~].*)?$' /app/requirements.txt > /tmp/requirements.docker.txt \
    && python -m pip install \
        --no-cache-dir \
        --retries ${PIP_RETRIES} \
        --timeout ${PIP_DEFAULT_TIMEOUT} \
        -i ${PIP_INDEX_URL} \
        --trusted-host ${PIP_TRUSTED_HOST} \
        -r /tmp/requirements.docker.txt

COPY backend /app/backend
COPY data_pipeline /app/data_pipeline
COPY app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
