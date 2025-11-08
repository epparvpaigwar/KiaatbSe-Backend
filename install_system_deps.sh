#!/bin/bash
# System Dependencies Installation Script for KiaatbSe Backend
# This script installs Tesseract OCR and Poppler utilities

set -e  # Exit on error

echo "=========================================="
echo "KiaatbSe Backend - System Dependencies"
echo "=========================================="
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS. Please install manually."
    exit 1
fi

echo "Detected OS: $OS"
echo ""

# Install based on OS
case "$OS" in
    ubuntu|debian)
        echo "Installing for Ubuntu/Debian..."
        sudo apt-get update
        sudo apt-get install -y tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng poppler-utils
        ;;

    centos|rhel|fedora)
        echo "Installing for CentOS/RHEL/Fedora..."
        sudo yum install -y epel-release
        sudo yum install -y tesseract tesseract-langpack-hin tesseract-langpack-eng poppler-utils
        ;;

    alpine)
        echo "Installing for Alpine Linux..."
        sudo apk add --no-cache tesseract-ocr tesseract-ocr-data-hin tesseract-ocr-data-eng poppler-utils
        ;;

    *)
        echo "Unsupported OS: $OS"
        echo "Please refer to SYSTEM_DEPENDENCIES.md for manual installation"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Verifying Installation..."
echo "=========================================="
echo ""

# Verify Tesseract
if command -v tesseract &> /dev/null; then
    echo "✓ Tesseract installed:"
    tesseract --version | head -1
    echo ""
    echo "  Available languages:"
    tesseract --list-langs 2>&1 | grep -E "eng|hin" || echo "  WARNING: Hindi (hin) or English (eng) not found!"
else
    echo "✗ Tesseract NOT found in PATH"
    exit 1
fi

echo ""

# Verify Poppler
if command -v pdftoimage &> /dev/null || command -v pdftoppm &> /dev/null; then
    echo "✓ Poppler utilities installed:"
    pdftoimage -v 2>&1 | head -1 || pdftoppm -v 2>&1 | head -1
else
    echo "✗ Poppler utilities NOT found in PATH"
    exit 1
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Install Python dependencies: pip install -r requirements.txt"
echo "2. Restart your Django server (Gunicorn/uWSGI)"
echo ""
