# SOLUTION: Use Docker for Render Deployment

## Problem

❌ **Aptfile does NOT work on Render.com**
- Render doesn't support Heroku-style buildpacks
- System packages cannot be installed via Aptfile
- That's why tesseract errors persisted even after adding Aptfile

## Solution

✅ **Use Docker** - The correct way to install system packages on Render

A Dockerfile has been created that:
- Installs tesseract-ocr (with Hindi & English)
- Installs poppler-utils (for PDF processing)
- Sets up your Python environment
- Runs your Django app

---

## Quick Deploy Steps

### 1. Commit Files
```bash
git add Dockerfile .dockerignore
git commit -m "Add Dockerfile for Render with OCR support"
git push origin main
```

### 2. Update Render Settings

Go to Render Dashboard → Your Service → Settings:

- **Build Command:** (leave empty)
- **Start Command:** (leave empty)
- Render will auto-detect the Dockerfile

### 3. Deploy

Click **Manual Deploy** → **Clear build cache & deploy**

### 4. Verify

Build logs should show:
```
==> Building with Dockerfile...
Step 4/8 : RUN apt-get install -y tesseract-ocr...
```

OCR will work after this deployment! ✅

---

## Files Created

- ✅ `Dockerfile` - Defines container with tesseract & poppler
- ✅ `.dockerignore` - Optimizes Docker build
- ✅ `RENDER_DEPLOY.md` - Full deployment documentation
- ❌ Removed `Aptfile` - Not supported on Render

---

## Why This Works

**Docker gives you full control:**
- You can install ANY system package via `apt-get`
- The container includes tesseract, poppler, and all dependencies
- Render fully supports Docker deployments
- This is the official Render solution for system packages

---

## Reference

[Render Community: Install Additional Packages](https://community.render.com/t/install-additional-packages/280)

The community confirms: **Use Docker for system packages on Render.**
