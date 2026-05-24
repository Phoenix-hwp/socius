# Socius Framework — 最小可运行镜像
# 基于 Python 3.11

FROM python:3.11-slim

LABEL org.opencontainers.image.title="Socius — AI Work Partner"
LABEL org.opencontainers.image.description="Cognitive Engine + Decision Framework + Task Orchestration"
LABEL org.opencontainers.image.source="https://github.com/socius/socius"

WORKDIR /socius

# 安装依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# 复制框架层
COPY core/ ./core/
COPY adapters/ ./adapters/
COPY socius_cli.py .

# 环境变量（模型 API Key 通过 docker-compose 或 -e 传入）
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# 默认模型为本地 Ollama
ENV SOCIUS_MODEL=ollama-local

ENTRYPOINT ["python", "socius_cli.py"]
CMD ["verify"]
