# ─────────────────────────────────────────────────────────────────────────────
# AutoJustice AI NEXUS — Dockerfile
# Multi-stage build: slim Python + Tesseract OCR
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# Install system dependencies: Tesseract + poppler (for pdf2image) + build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-eng \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/

# Create required directories and non-root user
RUN mkdir -p backend/uploads backend/firs \
    && useradd -m -u 1000 appuser \
    && chown -R appuser:appuser /app

# Set environment variables
ENV PYTHONPATH=/app/backend
ENV TESSERACT_PATH=tesseract

USER appuser

# Expose port (Render/Cloud Run inject $PORT at runtime)
EXPOSE 8000
ENV PORT=8000

# WORKDIR backend so relative paths (templates/, static/) work, then uvicorn main:app.
# Shell form so ${PORT} expands on Render (sets PORT=10000 by default).
WORKDIR /app/backend
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2
