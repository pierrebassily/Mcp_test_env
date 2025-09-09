# Dockerfile.base
FROM python:3.11-slim AS mcp_base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
ENV PATH="/root/.local/bin:${PATH}"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app

# Copy dependency files and install directly to system site-packages
COPY requirements.txt ./
RUN uv pip install --system -r requirements.txt