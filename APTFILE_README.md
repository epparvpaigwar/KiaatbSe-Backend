# Aptfile - System Dependencies for Render

## What is this file?

The `Aptfile` tells Render which Ubuntu system packages to install before building your app.

## Contents

```
tesseract-ocr         # OCR engine for text extraction
tesseract-ocr-hin     # Hindi language support
tesseract-ocr-eng     # English language support
poppler-utils         # PDF to image conversion tools
```

## How it works

1. When you deploy to Render, it automatically detects the `Aptfile`
2. Render installs all packages listed in this file
3. Then it runs your Build Command (`pip install -r requirements.txt`)
4. Your app can now use tesseract and poppler

## DO NOT DELETE THIS FILE

Your OCR functionality requires these system packages. Without the `Aptfile`, your PDF processing will fail with errors like:

```
tesseract is not installed or it's not in your PATH
```

## Learn more

- Render Aptfile docs: https://render.com/docs/native-environments#apt-packages
- See RENDER_DEPLOY.md for complete deployment guide
