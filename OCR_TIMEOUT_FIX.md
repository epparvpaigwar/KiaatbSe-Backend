# Fix for OCR Worker Timeout

## Problem

After Docker deployment worked, OCR processing was timing out:

```
[CRITICAL] WORKER TIMEOUT (pid:25)
[ERROR] Worker (pid:25) was sent SIGKILL! Perhaps out of memory?
```

This happened because:
1. **OCR processing is slow** - Especially on Render's free tier (0.1 CPU)
2. **Default Gunicorn timeout is 30 seconds** - OCR takes much longer for large files
3. **High DPI (300) was very slow** - Processing high-res images is CPU intensive
4. **Large PDFs (100+ pages)** - Can take 10-30 minutes to process

---

## Solutions Applied

### 1. Increased Gunicorn Timeout (Dockerfile)

**Before:**
```dockerfile
CMD gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT
```

**After:**
```dockerfile
CMD gunicorn backend.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --timeout 1800 \
    --workers 2 \
    --worker-class sync \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --graceful-timeout 60 \
    --keep-alive 5
```

**Changes:**
- `--timeout 1800` - Allows **30 minutes** for OCR processing (for large PDFs with 100+ pages)
- `--workers 2` - Uses 2 worker processes for better concurrency
- `--worker-class sync` - Synchronous workers (better for long-running tasks)
- `--max-requests 1000` - Restart workers after 1000 requests (prevents memory leaks)
- `--max-requests-jitter 100` - Adds randomness to prevent all workers restarting simultaneously
- `--graceful-timeout 60` - Allows 60 seconds for graceful worker shutdown
- `--keep-alive 5` - Keeps connections alive for 5 seconds

### 2. Reduced OCR DPI (pdf_processor_ocr.py)

**Before:**
```python
dpi=300,  # High resolution for better OCR
```

**After:**
```python
dpi=150,  # Reduced DPI for faster processing (was 300)
```

**Benefits:**
- **~4x faster** processing (DPI reduction from 300 to 150)
- **Less memory usage** - Smaller images
- **Still good quality** - 150 DPI is sufficient for text OCR
- **Lower CPU usage** - Faster tesseract processing

---

## Deploy These Changes

```bash
git add Dockerfile audiobooks/services/pdf_processor_ocr.py
git commit -m "Fix OCR timeout: increase Gunicorn timeout and reduce DPI"
git push origin main
```

Render will auto-deploy and rebuild with these changes.

---

## Expected Result

After deployment:
- ✅ OCR will complete without timeout
- ✅ PDFs will process successfully
- ✅ Worker won't get killed
- ⚡ Faster processing time

---

## Testing

After deployment, try uploading a PDF:

1. Upload a PDF through your API
2. Check logs - should see:
   ```
   Converting PDF to images...
   Processing X images with Tesseract OCR
   OCR extracted page 1/X (XXXX chars)
   ```
3. No timeout errors!

---

## If Still Times Out (Unlikely)

If PDFs with many pages (20+) still timeout:

### Option 1: Process in Background (Recommended Long-term)

You already have Celery configured! Move OCR to a Celery task:

```python
# In tasks.py
@shared_task
def process_pdf_with_ocr(pdf_path, book_id):
    result = PDFProcessorOCR.extract_pages_with_ocr(pdf_path)
    # Save result to database
    return result

# In views.py
# Instead of processing immediately, queue it:
process_pdf_with_ocr.delay(pdf_path, book.id)
return Response({"message": "Processing started"})
```

### Option 2: Further Reduce DPI

Change DPI from 150 to 100 in pdf_processor_ocr.py:
```python
dpi=100,  # Even faster, still readable
```

### Option 3: Limit Pages

Process only first 50 pages for very large PDFs.

---

## Performance on Free Tier

**Render Free Tier Limits:**
- CPU: 0.1 CPU (shared)
- RAM: 512 MB
- Timeout: Now **1800 seconds (30 minutes)**

**Expected Processing Times (with DPI=150):**
- 1-page PDF: ~5-10 seconds
- 10-page PDF: ~30-60 seconds
- 50-page PDF: ~3-5 minutes
- 100-page PDF: ~10-15 minutes
- 200-page PDF: ~20-30 minutes (should work now!)
- 300+ pages: Consider using Celery background tasks

---

## Monitoring

Watch the logs during upload:

```
Converting PDF to images...
Processing 8 images with Tesseract OCR
OCR extracted page 1/8 (1234 chars)
OCR extracted page 2/8 (2345 chars)
...
OCR extracted page 8/8 (1567 chars)
```

If you see all pages complete → ✅ Working!

If you see WORKER TIMEOUT → Need Celery for large PDFs
