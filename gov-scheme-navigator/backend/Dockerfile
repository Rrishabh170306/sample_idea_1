FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        wget gnupg ca-certificates fonts-liberation libnss3 libatk1.0-0 libatk-bridge2.0-0 libx11-xcb1 \
        libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2 libxss1 libxtst6 libpangocairo-1.0-0 \
        libcups2 libgtk-3-0 libgdk-pixbuf-xlib-2.0-0 fonts-dejavu-core shared-mime-info \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .[llm] \
    && python -m playwright install --with-deps

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
