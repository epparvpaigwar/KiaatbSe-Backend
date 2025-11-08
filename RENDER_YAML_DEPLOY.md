# Deploy with render.yaml (Docker)

## What Changed

Updated `render.yaml` to use **Docker** instead of Python:

**Before:**
```yaml
env: python
buildCommand: "pip install -r requirements.txt"
```

**After:**
```yaml
runtime: docker
dockerfilePath: ./Dockerfile
```

---

## Steps to Deploy

### 1. Commit and Push

```bash
git add render.yaml Dockerfile .dockerignore
git commit -m "Switch to Docker deployment with render.yaml"
git push origin main
```

### 2. Render Will Auto-Detect

Render automatically reads `render.yaml` from your repo and will:
- Detect `runtime: docker`
- Build using your Dockerfile
- Install tesseract and poppler

### 3. Verify Build Logs

After push, check your Render dashboard. Build logs should show:

```
==> Building with Dockerfile...
Step 1/8 : FROM python:3.11-slim
Step 4/8 : RUN apt-get install -y tesseract-ocr tesseract-ocr-hin...
```

NOT:
```
==> Installing Python version 3.11.11...  ❌
```

---

## Important Notes

### Environment Variables

The `render.yaml` has `sync: false` for sensitive env vars like:
- SECRET_KEY
- DATABASE_URL
- CLOUDINARY_*
- REDIS_URL
- SENDGRID_API_KEY

This means they **won't be changed** - your existing environment variables in Render Dashboard will continue to work.

### What Gets Used

- ✅ **Dockerfile** - For building the container
- ✅ **render.yaml** - For service configuration
- ✅ **Existing env vars** - From Render Dashboard (unchanged)

---

## If It Still Uses Python

If Render ignores the render.yaml and keeps using Python:

### Option A: Delete and Recreate Service

1. **Save your environment variables** (copy them somewhere)
2. **Delete the old service** in Render Dashboard
3. Render will **auto-create a new service** from render.yaml
4. It will use Docker this time
5. **Re-add environment variables** that have `sync: false`

### Option B: Use Render Blueprint

Go to Render Dashboard:
1. Click **"Blueprints"** in the sidebar
2. Click **"New Blueprint Instance"**
3. Connect your GitHub repo
4. Render will read render.yaml and create Docker service

---

## Expected Result

After deployment:
- ✅ OCR will work (tesseract installed)
- ✅ PDF processing will work (poppler installed)
- ✅ No more "tesseract is not installed" errors

---

## Troubleshooting

**Still seeing Python build?**
- Delete the service and let Render recreate it from render.yaml
- OR use the Blueprint method above

**Environment variables missing?**
- Go to Settings → Environment
- Manually add the ones marked `sync: false` in render.yaml
- Redeploy

**Docker build fails?**
- Check that Dockerfile exists in repo root
- Verify commit was pushed: `git log --oneline -1`
- Check Render connected to correct branch (main)
