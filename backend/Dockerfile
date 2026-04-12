# Dockerfile for Internship Assistant Backend
FROM python:3.11

WORKDIR /app

# Install system dependencies for Python packages and Playwright
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    wget \
    gnupg \
    ca-certificates \
    # For lxml, scrapy, etc.
    libxml2-dev \
    libxslt-dev \
    # For image processing (if needed)
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    # For scikit-learn
    libopenblas-dev \
    liblapack-dev \
    gfortran \
    # For Playwright runtime dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    # Clean up to reduce image size
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 配置pip使用国内镜像源加速下载
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn && \
    pip config set global.timeout 100 && \
    pip config set global.retries 5

# Copy requirements first for better caching
COPY requirements.txt .

# 分步安装依赖包，提高稳定性
RUN pip install --no-cache-dir --upgrade pip && \
    # 先安装基础依赖
    pip install --no-cache-dir fastapi uvicorn && \
    # 安装其他依赖，增加重试机制
    echo "Installing dependencies from requirements.txt..." && \
    pip install --no-cache-dir -r requirements.txt || \
    (echo "首次安装失败，5秒后重试..." && sleep 5 && pip install --no-cache-dir -r requirements.txt)

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]