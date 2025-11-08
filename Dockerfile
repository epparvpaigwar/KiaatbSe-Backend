# Use official Python runtime as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies (including tesseract, poppler, and ffmpeg)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-eng \
    poppler-utils \
    libpq-dev \
    gcc \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . /app/

# Expose port (Render will override this with $PORT)
EXPOSE 10000

# Run gunicorn with extended timeout for large file OCR processing
CMD gunicorn backend.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --timeout 1800 \
    --workers 2 \
    --worker-class sync \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --graceful-timeout 60 \
    --keep-alive 5
