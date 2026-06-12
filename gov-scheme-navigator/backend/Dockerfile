FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System dependencies: Playwright, OCR (tesseract), PDF processing
RUN apt-get update && apt-get install -y --no-install-recommends \
        # Playwright Chromium dependencies
        wget gnupg ca-certificates \
        fonts-liberation libnss3 libatk1.0-0 libatk-bridge2.0-0 \
        libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
        libasound2 libxss1 libxtst6 libpangocairo-1.0-0 libcups2 \
        libgtk-3-0 libgdk-pixbuf-xlib-2.0-0 fonts-dejavu-core \
        shared-mime-info \
        # OCR
        tesseract-ocr tesseract-ocr-hin tesseract-ocr-tam \
        # PDF support
        libmupdf-dev \
        # General utilities
        curl netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specification
COPY pyproject.toml ./

# Install ALL Python dependencies (base + all extras)
RUN pip install --upgrade pip && \
    pip install ".[dev]" && \
    pip install \
        asyncpg \
        pgvector \
        sentence-transformers \
        playwright \
        scrapy \
        pymupdf \
        pytesseract \
        alembic \
        redis \
        neo4j \
        langgraph \
        langchain \
        langchain-community \
        httpx \
        prometheus-client && \
    python -m playwright install chromium --with-deps

# Copy application code
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Copy startup script
COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# Create data directory for profile store
RUN mkdir -p /app/data

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
