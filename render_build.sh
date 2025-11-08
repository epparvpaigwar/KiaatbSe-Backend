#!/usr/bin/env bash
# Render.com Build Script
# Installs system dependencies and Python packages

set -o errexit  # Exit on error

echo "Installing system dependencies..."
apt-get update
apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-eng \
    poppler-utils

echo "System dependencies installed successfully!"
echo ""

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Build complete!"
