# 使用官方Python镜像替代GitHub Container Registry
FROM python:3.10-slim-bookworm

# 可配置 PIP 与 APT 源（有全球代理时建议用官方 PyPI 与默认 Debian 源）
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG APT_MIRROR=default

# 安装uv包管理器
RUN pip install -i ${PIP_INDEX_URL} uv

WORKDIR /app

RUN mkdir -p /app/data /app/logs

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN if [ "$APT_MIRROR" = "aliyun" ]; then \
      echo 'deb http://mirrors.aliyun.com/debian/ bookworm main' > /etc/apt/sources.list && \
      echo 'deb-src http://mirrors.aliyun.com/debian/ bookworm main' >> /etc/apt/sources.list && \
      echo 'deb http://mirrors.aliyun.com/debian/ bookworm-updates main' >> /etc/apt/sources.list && \
      echo 'deb-src http://mirrors.aliyun.com/debian/ bookworm-updates main' >> /etc/apt/sources.list && \
      echo 'deb http://mirrors.aliyun.com/debian-security bookworm-security main' >> /etc/apt/sources.list && \
      echo 'deb-src http://mirrors.aliyun.com/debian-security bookworm-security main' >> /etc/apt/sources.list ; \
    else \
      echo 'Using default Debian sources (deb.debian.org)'; \
    fi

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wkhtmltopdf \
    xvfb \
    fonts-wqy-zenhei \
    fonts-wqy-microhei \
    fonts-liberation \
    pandoc \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 启动Xvfb虚拟显示器
RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1024x768x24 -ac +extension GLX &\nexport DISPLAY=:99\nexec "$@"' > /usr/local/bin/start-xvfb.sh \
    && chmod +x /usr/local/bin/start-xvfb.sh

COPY pyproject.toml ./
COPY uv.lock* ./
COPY . .

# 使用 uv 直接安装项目（确保 -e 安装生效，带完整依赖）
RUN uv pip install --system -e . --index-url ${PIP_INDEX_URL}

# 确保安装新版Google GenAI SDK和其他多模型依赖
# 兜底补齐关键依赖（容器内导入常见缺项）
RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} \
    google-genai>=1.29.0 \
    langgraph>=0.4.8 \
    langchain-google-genai>=2.1.5 \
    pyyaml>=6.0 \
    requests>=2.32.0

# 为运行时提供必要的系统字体/工具，Plotly导出PNG/SVG已可用（可选）

# 复制日志配置文件
# 确保配置目录存在
RUN mkdir -p /app/config && cp -r config/ /app/ || true

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "web/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
