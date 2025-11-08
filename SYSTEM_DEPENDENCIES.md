# System Dependencies for KiaatbSe Backend

This project requires certain system-level dependencies to be installed on the server for OCR and PDF processing functionality.

## Required System Packages

### 1. Tesseract OCR
Required for optical character recognition (Hindi and English text extraction from PDFs)

### 2. Poppler Utils
Required for PDF to image conversion (used by pdf2image library)

---

## Installation Instructions

### For Ubuntu/Debian (Most common for servers)

```bash
# Update package list
sudo apt-get update

# Install Tesseract OCR with Hindi language support
sudo apt-get install -y tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng

# Install Poppler utilities
sudo apt-get install -y poppler-utils

# Verify installations
tesseract --version
tesseract --list-langs  # Should show: eng, hin
pdftoimage -v
```

### For CentOS/RHEL/Fedora

```bash
# Install EPEL repository (if not already installed)
sudo yum install -y epel-release

# Install Tesseract and language data
sudo yum install -y tesseract tesseract-langpack-hin tesseract-langpack-eng

# Install Poppler utilities
sudo yum install -y poppler-utils

# Verify installations
tesseract --version
tesseract --list-langs
pdftoimage -v
```

### For Alpine Linux (Docker)

```dockerfile
# Add to your Dockerfile
RUN apk add --no-cache \
    tesseract-ocr \
    tesseract-ocr-data-hin \
    tesseract-ocr-data-eng \
    poppler-utils
```

### For macOS (Development)

```bash
# Using Homebrew
brew install tesseract tesseract-lang poppler

# Verify
tesseract --version
tesseract --list-langs
```

---

## Verification

After installation, verify the dependencies are working:

```bash
# Check Tesseract
tesseract --version
tesseract --list-langs  # Should include 'eng' and 'hin'

# Check Poppler
pdftoimage -v
pdftoppm -v

# Check if in PATH
which tesseract
which pdftoimage
```

---

## Python Dependencies

The Python packages are already in `requirements.txt`:
- pytesseract==0.3.13
- pdf2image==1.17.0
- Pillow==11.2.1
- pdfplumber==0.11.4

Install with:
```bash
pip install -r requirements.txt
```

---

## Troubleshooting

### Error: "tesseract is not installed or it's not in your PATH"

**Solution:**
1. Install tesseract-ocr package (see above)
2. Ensure it's in system PATH
3. Restart your application server after installation

### Error: "Unable to get page count. Is poppler installed?"

**Solution:**
1. Install poppler-utils package (see above)
2. Ensure pdftoimage/pdftoppm are in PATH
3. Restart your application server

### Hindi text not working

**Solution:**
1. Install Hindi language data: `tesseract-ocr-hin` or `tesseract-langpack-hin`
2. Verify with: `tesseract --list-langs` (should show 'hin')

---

## For Render.com (Free Tier)

If you're deploying to Render.com:

**Option 1: Direct Build Command (Quick)**

In your Render dashboard → Settings → Build Command, use:
```bash
apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng poppler-utils && pip install -r requirements.txt
```

**Option 2: Using Build Script (Recommended)**

1. Commit the `render_build.sh` file to your repository
2. In Render dashboard → Settings → Build Command, use:
   ```bash
   ./render_build.sh
   ```

**Important:** Keep this Build Command permanently! Render rebuilds from scratch on every deploy.

---

## For DomCloud Hosting

If you're using DomCloud or similar shared hosting:

1. **SSH into your server**
2. **Check if you have sudo access:**
   ```bash
   sudo apt-get update
   ```

3. **If you have sudo access**, run the Ubuntu/Debian commands above

4. **If you DON'T have sudo access**, contact your hosting support and request:
   - tesseract-ocr with Hindi language support
   - poppler-utils

5. **Alternative:** Some shared hosting may have these pre-installed. Check first:
   ```bash
   which tesseract
   tesseract --list-langs
   which pdftoimage
   ```

---

## Contact Hosting Support

If you cannot install these yourself, send this message to your hosting provider:

> Hi, I need the following system packages installed on my server for my Python Django application:
>
> 1. tesseract-ocr (with English and Hindi language data)
> 2. poppler-utils
>
> These are required for PDF processing and OCR functionality.
>
> Installation command for Ubuntu/Debian:
> ```
> sudo apt-get install -y tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng poppler-utils
> ```

---

## Notes

- These are **system-level** dependencies and cannot be installed via pip
- They must be installed on the server where your Django application runs
- After installation, restart your Django application/server (Gunicorn, uWSGI, etc.)
- The Python packages (pytesseract, pdf2image) are just wrappers that call these system binaries
