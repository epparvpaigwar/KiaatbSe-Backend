# Render.com Deployment Guide

## Fix OCR Error on Render

Your OCR is failing because Render doesn't have tesseract and poppler installed by default.

### Quick Fix (2 minutes)

1. Go to your **Render Dashboard**
2. Select your web service
3. Go to **Settings** tab
4. Find **Build Command** section
5. Replace the current command with:

```bash
apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng poppler-utils && pip install -r requirements.txt
```

6. Click **Save Changes**
7. Click **Manual Deploy** → **Deploy latest commit**

### What this does:

- `tesseract-ocr` - Installs Tesseract OCR engine
- `tesseract-ocr-hin` - Adds Hindi language support
- `tesseract-ocr-eng` - Adds English language support
- `poppler-utils` - Installs PDF to image conversion tools
- `pip install -r requirements.txt` - Installs Python packages

### After deployment:

Your OCR errors will be gone! The system will be able to:
- Extract text from PDFs using OCR
- Process Hindi and English text
- Convert PDF pages to images

### Important Notes:

⚠️ **Keep this Build Command permanently!**
- Render rebuilds from scratch on every deploy
- If you remove these system packages, OCR will break again
- This is not a one-time fix - it needs to run on every build

### Alternative: Use Build Script

If you prefer a cleaner approach, you can use the `render_build.sh` script:

1. Make sure `render_build.sh` is committed to your git repo
2. In Render Build Command, use:
   ```bash
   ./render_build.sh
   ```

This is the same thing, just organized in a script file.

---

## Complete Render Configuration

Here's what your Render settings should look like:

**Build Command:**
```bash
apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-hin tesseract-ocr-eng poppler-utils && pip install -r requirements.txt
```

**Start Command:**
```bash
gunicorn backend.wsgi:application
```

**Environment Variables:**
- Add all variables from your `.env` file
- Make sure `DEBUG=False` in production
- Set `ALLOWED_HOSTS` to include your Render domain

---

## Testing

After deployment, test OCR by uploading a PDF through your API:

```bash
curl -X POST https://your-app.onrender.com/api/books/upload/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.pdf"
```

You should see text extracted without errors in the logs.

---

## Troubleshooting

**If you still see OCR errors:**

1. Check Render build logs - ensure packages installed successfully
2. Verify Hindi language is available:
   - In Render logs during build, look for "tesseract-ocr-hin"
3. Check your application logs for specific errors
4. Make sure you clicked "Manual Deploy" after changing Build Command

**Build failing?**

- Check if build command syntax is correct (no typos)
- Make sure render_build.sh has execute permissions if using script method
- Check Render's build logs for specific error messages
