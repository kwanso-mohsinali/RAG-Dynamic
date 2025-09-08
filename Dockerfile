# ===============================
# Base image
# ===============================
FROM --platform=linux/amd64 python:3.13.5-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libmagic-dev \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-script-latn \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY apps/api/requirements.txt ./requirements.txt

# Install Python dependencies with optimizations
RUN pip install --upgrade pip==25.1.1 && \
    pip install --no-cache-dir --default-timeout=100 --retries=5 \
    --prefer-binary -r requirements.txt

# ===============================
# Runtime image
# ===============================
FROM base AS runtime
WORKDIR /app
COPY apps/api .

# Set Python path to include the current directory
ENV PYTHONPATH=/app:$PYTHONPATH

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
