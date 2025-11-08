# Use official Python runtime as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies (including tesseract and poppler)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-eng \
    poppler-utils \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files
COPY . /app/

# Expose port (Render will override this with $PORT)
EXPOSE 10000

# Run gunicorn with extended timeout for large file OCR processing
# --timeout 1800 = 30 minutes (for large PDFs with 100+ pages)
# --workers 2 = 2 worker processes
# --worker-class sync = Synchronous workers (better for long-running tasks)
# --max-requests 1000 = Restart workers after 1000 requests (prevent memory leaks)
# --max-requests-jitter 100 = Add randomness to prevent all workers restarting at once
CMD gunicorn backend.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --timeout 1800 \
    --workers 2 \
    --worker-class sync \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --graceful-timeout 60 \
    --keep-alive 5
