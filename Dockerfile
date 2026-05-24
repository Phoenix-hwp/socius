# Phoenix Framework — 最小可运行镜像
# 基于 Python 3.11 + Node.js（适配器的双运行时支持）

FROM python:3.11-slim

LABEL org.opencontainers.image.title="Phoenix AI-Knowledge Framework"
LABEL org.opencontainers.image.description="Cognitive Engine + Decision Framework + Task Orchestration"
LABEL org.opencontainers.image.source="https://github.com/phoenixhwp/phoenix"

# Node.js 运行时（Cursor 适配器的 .mjs 钩子需要）
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /phoenix

# 安装依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .[dev] 2>/dev/null || pip install --no-cache-dir -e .

# 复制框架层
COPY core/ ./core/
COPY adapters/ ./adapters/
COPY protocols/ ./protocols/
COPY phoenix_cli.py .

# 环境变量（模型 API Key 通过 docker-compose 或 -e 传入）
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# 默认模型为本地 Ollama
ENV PHOENIX_MODEL=ollama-local

ENTRYPOINT ["python", "phoenix_cli.py"]
CMD ["verify"]
