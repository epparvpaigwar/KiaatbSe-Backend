# Render.com Deployment Guide

## Fix OCR Error on Render

**IMPORTANT:** Render does NOT support Aptfile like Heroku. You must use Docker to install system packages.

## Solution: Use Docker Deployment

A Dockerfile has been created that includes tesseract and poppler system packages.

### Steps to Deploy with Docker:

1. **Commit the Dockerfile:**
   ```bash
   git add Dockerfile .dockerignore
   git commit -m "Add Dockerfile for Render deployment with OCR dependencies"
   git push origin main
   ```

2. **Update Render Settings:**

   Go to your Render Dashboard → Your Service → Settings:

   **Build & Deploy:**
   - **Build Command:** Leave EMPTY (Docker will handle it)
   - **Start Command:** Leave EMPTY (Dockerfile CMD will handle it)
   - **Dockerfile Path:** `Dockerfile` (or leave default)

3. **Deploy:**
   - Click **Manual Deploy** → **Clear build cache & deploy**
   - Wait for Docker image to build

4. **Verify in Build Logs:**
   You should see:
   ```
   ==> Building with Dockerfile...
   Step 4/8 : RUN apt-get update && apt-get install -y tesseract-ocr...
   ```

### What the Dockerfile Does:

- Uses Python 3.11 slim image
- Installs system packages:
  - `tesseract-ocr` - OCR engine
  - `tesseract-ocr-hin` - Hindi language support
  - `tesseract-ocr-eng` - English language support
  - `poppler-utils` - PDF to image conversion
  - `libpq-dev` - PostgreSQL support
  - `gcc` - Compiler for some Python packages
- Installs Python dependencies from requirements.txt
- Runs gunicorn to serve Django app

---

## Why Docker Instead of Aptfile?

**Render does not support Aptfile.** Unlike Heroku or DigitalOcean App Platform, Render's native Python environment doesn't have a way to install system packages via Aptfile.

The solutions for installing system packages on Render are:
1. **Docker** (recommended) - Full control over environment
2. **Native builds** - Very limited, can't install arbitrary packages

---

## Complete Render Configuration (Docker)

**Files in your repo:**
- `Dockerfile` - Defines the container environment
- `.dockerignore` - Optimizes Docker build
- `requirements.txt` - Python dependencies

**Render Settings:**
- **Environment:** Docker
- **Build Command:** (empty)
- **Start Command:** (empty)
- **Dockerfile Path:** Dockerfile

**Environment Variables:**
- Add all variables from your `.env` file
- `SECRET_KEY`
- `DATABASE_URL`
- `CLOUDINARY_*`
- `REDIS_URL`
- `SENDGRID_API_KEY`
- etc.

---

## Testing

After deployment, upload a PDF through your API:

```bash
curl -X POST https://your-app.onrender.com/api/books/upload/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.pdf"
```

Check logs - you should see text extracted without "tesseract not installed" errors.

---

## Troubleshooting

### Build fails with "Cannot find Dockerfile"
- Make sure Dockerfile is in the root of your repo
- Check "Dockerfile Path" in Render settings is set to `Dockerfile`

### Still getting tesseract errors
- Check build logs to ensure tesseract was installed during Docker build
- Look for lines like: `Step 4/8 : RUN apt-get install -y tesseract-ocr`
- Make sure you deployed AFTER committing Dockerfile

### Environment variables not working
- Go to Render Dashboard → Environment
- Add all necessary variables
- Redeploy after adding variables

---

## Migrating from Native Python to Docker

If you previously had a native Python deployment:

1. Commit the Dockerfile to your repo
2. In Render Dashboard, you don't need to delete the service
3. Just push the Dockerfile and redeploy
4. Render will automatically detect the Dockerfile and switch to Docker builds
5. Update Build/Start commands to be empty (let Dockerfile handle it)

---

## Why the Aptfile Didn't Work

Aptfile is a Heroku buildpack feature that Render does not support. While some platforms like DigitalOcean App Platform support Aptfile, Render requires using Docker for custom system packages.

Reference: [Render Community - Install Additional Packages](https://community.render.com/t/install-additional-packages/280)
