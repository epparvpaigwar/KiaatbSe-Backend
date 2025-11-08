# Render.com Deployment Guide

## Fix OCR Error on Render

Your OCR is failing because Render doesn't have tesseract and poppler installed by default.

### Solution: Use Aptfile (Render's official method)

Render uses an `Aptfile` to install system packages. An `Aptfile` has been created in your repo.

**Steps:**

1. **Commit and push the Aptfile:**
   ```bash
   git add Aptfile
   git commit -m "Add system dependencies for OCR"
   git push origin main
   ```

2. **Ensure Build Command is simple:**
   - Go to Render Dashboard → Your Service → Settings
   - Build Command should be: `pip install -r requirements.txt`
   - If you changed it earlier, change it back

3. **Deploy:**
   - Render will auto-deploy on push, OR
   - Click **Manual Deploy** → **Deploy latest commit**

4. **Verify in build logs:**
   - Look for: "Installing dependencies from Aptfile"
   - Should see tesseract and poppler being installed

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

### Why Aptfile?

Render's build environment has a read-only filesystem, so you can't run `apt-get` directly. The `Aptfile` is Render's official way to install system packages - it works like `requirements.txt` but for Ubuntu packages.

---

## Complete Render Configuration

Here's what your Render settings should look like:

**Files in your repo:**
- `Aptfile` (contains system packages - already created)
- `requirements.txt` (contains Python packages)

**Build Command:**
```bash
pip install -r requirements.txt
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
