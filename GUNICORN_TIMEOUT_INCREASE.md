# Gunicorn Timeout Increased for Large File Uploads

## Summary of Changes

Increased Gunicorn timeout from **5 minutes to 30 minutes** to handle large PDF uploads.

---

## What Changed

### Dockerfile - Gunicorn Configuration

**Before (300 seconds = 5 minutes):**
```dockerfile
CMD gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --timeout 300 --workers 2
```

**After (1800 seconds = 30 minutes):**
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

---

## Configuration Explained

### `--timeout 1800` (30 minutes)
- Allows workers to process requests for up to 30 minutes before timing out
- **Why:** Large PDFs with 100-200 pages can take 15-30 minutes to OCR
- **Before:** Workers were killed after 5 minutes

### `--workers 2`
- Runs 2 worker processes
- **Why:** Allows concurrent request handling while conserving memory (512MB limit on free tier)
- **Best Practice:** 2-4 workers on 512MB RAM

### `--worker-class sync`
- Uses synchronous workers
- **Why:** Better for long-running, CPU-intensive tasks like OCR
- **Alternative:** `gevent` or `eventlet` for many concurrent connections (not needed for OCR)

### `--max-requests 1000`
- Restarts workers after 1000 requests
- **Why:** Prevents memory leaks by recycling workers
- **Best Practice:** Set to 1000-5000 for production

### `--max-requests-jitter 100`
- Adds randomness (0-100) to max-requests
- **Why:** Prevents all workers from restarting at the same time
- **Example:** Worker 1 restarts at 1050 requests, Worker 2 at 1023 requests

### `--graceful-timeout 60`
- Allows 60 seconds for workers to finish current requests before shutdown
- **Why:** Ensures ongoing requests complete before worker restarts
- **Best Practice:** Set to 30-120 seconds

### `--keep-alive 5`
- Keeps HTTP connections alive for 5 seconds
- **Why:** Improves performance for multiple requests from same client
- **Best Practice:** 2-5 seconds for web apps

---

## File Size & Processing Time Estimates

| PDF Pages | File Size | Processing Time (DPI=150) | Will It Work? |
|-----------|-----------|---------------------------|---------------|
| 1-10      | < 5 MB    | 10-60 seconds             | ✅ Yes        |
| 11-50     | 5-20 MB   | 1-5 minutes               | ✅ Yes        |
| 51-100    | 20-40 MB  | 5-15 minutes              | ✅ Yes        |
| 101-200   | 40-50 MB  | 15-30 minutes             | ✅ Yes (now!) |
| 200-300   | 50+ MB    | 30-45 minutes             | ⚠️ May timeout |
| 300+      | 50+ MB    | 45+ minutes               | ❌ Use Celery |

**Note:** Times are estimates on Render free tier (0.1 CPU shared)

---

## Deploy These Changes

```bash
git add Dockerfile OCR_TIMEOUT_FIX.md GUNICORN_TIMEOUT_INCREASE.md
git commit -m "Increase Gunicorn timeout to 30 minutes for large PDF uploads"
git push origin main
```

Render will auto-deploy with the new configuration.

---

## Testing

### Test Small File (should be fast)
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@small_10_pages.pdf" \
  -F "title=Test Small" \
  http://localhost:8000/api/books/upload/
```

Expected: ~30-60 seconds

### Test Medium File
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@medium_50_pages.pdf" \
  -F "title=Test Medium" \
  http://localhost:8000/api/books/upload/
```

Expected: ~3-5 minutes

### Test Large File
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@large_100_pages.pdf" \
  -F "title=Test Large" \
  http://localhost:8000/api/books/upload/
```

Expected: ~10-15 minutes

---

## Monitoring & Logs

### Watch Processing in Real-Time

In Render logs, you'll see:
```
Processing 100 pages with OCR (lang=hin+eng)
Converting PDF to images...
Processing 100 images with Tesseract OCR
OCR extracted page 1/100 (1234 chars)
OCR extracted page 2/100 (2345 chars)
...
OCR extracted page 100/100 (1567 chars)
```

### Check for Timeouts

If you still see timeout errors:
```
[CRITICAL] WORKER TIMEOUT (pid:25)
```

**Solutions:**
1. ✅ DPI is already reduced to 150
2. ✅ Timeout is now 30 minutes
3. ⚠️ If still timing out, file is too large - use Celery background tasks

---

## When to Use Celery Instead

For **extremely large files** (200+ pages), consider moving OCR to Celery background tasks:

### Benefits:
- ✅ No timeout limits
- ✅ User gets immediate response
- ✅ Processing happens in background
- ✅ User can check progress later

### Implementation:
```python
# tasks.py
from celery import shared_task

@shared_task
def process_large_pdf(book_id, pdf_path):
    result = PDFProcessorOCR.extract_pages_with_ocr(pdf_path)
    # Save result to database
    return result

# views.py
from .tasks import process_large_pdf

def upload_book(request):
    # Save book
    book = Book.objects.create(...)

    # Queue OCR processing
    process_large_pdf.delay(book.id, pdf_path)

    return Response({
        "message": "Upload started, processing in background",
        "book_id": book.id
    })
```

**Note:** You already have Celery configured! Check `backend/celery.py`

---

## Troubleshooting

### Still Getting Timeouts After 30 Minutes?

**Check file size:**
```bash
ls -lh uploaded_file.pdf
# If > 50MB, file is too large for synchronous processing
```

**Solutions:**
1. Use Celery background tasks (recommended for 200+ pages)
2. Further reduce DPI to 100 (faster but lower quality)
3. Process only first 100 pages for preview

### Memory Issues?

If you see:
```
[ERROR] Worker (pid:25) was sent SIGKILL! Perhaps out of memory?
```

**Solutions:**
1. Reduce DPI from 150 to 100
2. Reduce workers from 2 to 1 (but slower)
3. Add `--worker-tmp-dir /dev/shm` to Gunicorn command

---

## Summary

✅ **Timeout increased:** 5 minutes → **30 minutes**
✅ **Can now handle:** PDFs with up to **200 pages**
✅ **Better worker management:** Auto-restart prevents memory leaks
✅ **Graceful shutdown:** Ongoing requests complete before restart

**Next:** Consider implementing SSE (Server-Sent Events) for real-time progress updates!

See: `SSE_UPLOAD_API_DOCUMENTATION.md` for details.
