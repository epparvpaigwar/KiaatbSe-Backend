# Audio Generation Guide - How It Works

## 🔄 Is Audio Generation Synchronous or Asynchronous?

**Answer: ASYNCHRONOUS** ✅

Audio generation happens in the **background** using **Celery workers**. The upload API returns immediately after queuing the tasks.

---

## 📊 How The Process Works

### Step 1: Upload API (Immediate)
```
POST /api/books/upload/?stream=true

⏱️ Time: ~40 seconds (for 8-page book)
```

**What Happens:**
1. ✅ User uploads PDF
2. ✅ Gemini extracts text from all pages (~40s)
3. ✅ Book record created in database
4. ✅ BookPage records created with extracted text
5. ✅ **Audio tasks queued** (instant)
6. ✅ **API returns 200 OK**

**Response:**
```json
{
  "event": "completed",
  "data": {
    "book_id": 123,
    "title": "घर जमाई",
    "total_pages": 8,
    "status_url": "/api/books/123/status/",
    "message": "Upload completed! Audio generation is running in background."
  }
}
```

---

### Step 2: Audio Generation (Background - Asynchronous)
```
Celery Workers Processing Audio

⏱️ Time: ~30 seconds per page (in parallel)
```

**What Happens:**
1. 🎵 Celery worker picks up task
2. 📝 Reads text from BookPage
3. 🔊 Generates audio with Edge TTS
4. ☁️ Uploads audio to Cloudinary
5. ✅ Updates BookPage status to 'completed'
6. 📊 Updates overall book progress

**Logs You'll See:**
```
[AUDIO TASK] Page 1/8 - Task ID: abc-123 - Status: QUEUED ✓
[🎵 AUDIO TASK] Starting audio generation for Book 123, Page 1
[⏳ AUDIO TASK] Page 1 - Status: PENDING → PROCESSING
[📝 AUDIO TASK] Page 1 - Text length: 3045 chars
[🔊 AUDIO TASK] Page 1 - Generating audio with Edge TTS...
[✓ AUDIO TASK] Page 1 - Audio generated! Duration: 28s
[☁️  AUDIO TASK] Page 1 - Uploading to Cloudinary...
[✓ AUDIO TASK] Page 1 - Uploaded to Cloudinary
[✅ AUDIO TASK] Page 1 - COMPLETED! Audio URL: https://...
[📊 PROGRESS] Book 123 - 1/8 pages completed (12%)
```

---

## 🔍 How to Check If Audio Is Generated

### Method 1: Status API Endpoint (Recommended) ✅

**Endpoint:**
```
GET /api/books/<book_id>/status/
```

**Example Request:**
```bash
curl http://localhost:8000/api/books/123/status/
```

**Response:**
```json
{
  "data": {
    "book_id": 123,
    "title": "घर जमाई",
    "processing_status": "processing",  // or "completed"
    "processing_progress": 37,          // 0-100%
    "total_pages": 8,
    "pages_status": {
      "pending": 3,      // Not started yet
      "processing": 2,   // Currently generating
      "completed": 3,    // Audio ready!
      "failed": 0        // Failed to generate
    },
    "audio_ready": false,              // true when all done
    "pages_with_audio": 3,
    "estimated_time_remaining": "2 minutes",
    "created_at": "2025-01-23T10:00:00Z",
    "last_updated": "2025-01-23T10:02:30Z"
  },
  "status": "PASS",
  "message": "Book processing status retrieved successfully"
}
```

**When All Audio is Generated:**
```json
{
  "data": {
    "processing_status": "completed",
    "processing_progress": 100,
    "audio_ready": true,
    "pages_with_audio": 8,
    "estimated_time_remaining": "Complete!"
  }
}
```

---

### Method 2: Poll the Status API

**Frontend Implementation:**
```javascript
async function trackAudioGeneration(bookId) {
  const checkStatus = async () => {
    const response = await fetch(`/api/books/${bookId}/status/`);
    const data = await response.json();

    console.log(`Progress: ${data.data.processing_progress}%`);
    console.log(`Pages with audio: ${data.data.pages_with_audio}/${data.data.total_pages}`);

    if (data.data.audio_ready) {
      console.log("✅ All audio generated!");
      return true; // Stop polling
    }

    return false; // Continue polling
  };

  // Poll every 5 seconds
  const intervalId = setInterval(async () => {
    const done = await checkStatus();
    if (done) {
      clearInterval(intervalId);
    }
  }, 5000);
}

// Usage after upload completes
trackAudioGeneration(123);
```

---

### Method 3: Check Individual Pages

**Endpoint:**
```
GET /api/books/<book_id>/pages/
```

**Response:**
```json
{
  "data": {
    "book": {
      "id": 123,
      "title": "घर जमाई",
      "total_pages": 8,
      "processing_status": "processing"
    },
    "pages": [
      {
        "id": 1,
        "page_number": 1,
        "text_content": "घर जमाई\nहरिधन...",
        "audio_url": "https://res.cloudinary.com/.../page_0001.mp3",
        "audio_duration": 28,
        "processing_status": "completed"  // ✅ Audio ready!
      },
      {
        "id": 2,
        "page_number": 2,
        "audio_url": null,
        "processing_status": "processing"  // ⏳ Still generating
      },
      {
        "id": 3,
        "page_number": 3,
        "audio_url": null,
        "processing_status": "pending"  // 🔜 Not started
      }
    ]
  }
}
```

---

## 📋 Page Processing Statuses

| Status | Meaning | Audio Available? |
|--------|---------|------------------|
| **pending** | Task queued, not started | ❌ No |
| **processing** | Currently generating audio | ❌ No |
| **completed** | Audio generated successfully | ✅ Yes |
| **failed** | Audio generation failed | ❌ No |

---

## ⏱️ Typical Timeline (8-Page Book)

```
00:00 - Upload starts
00:40 - Text extraction complete (Gemini)
00:40 - Audio tasks queued (all 8 pages)
00:40 - API returns 200 OK ✅

        [Background - Celery Workers]
00:40 - Page 1 audio starts
01:10 - Page 1 audio complete (30s)
01:10 - Page 2 audio starts
01:40 - Page 2 audio complete (30s)
...
04:00 - All audio complete! 🎉
```

**Total Time:**
- **Upload API**: 40 seconds ⚡
- **Audio Generation**: ~4 minutes (background) 🎵

---

## 🚀 Parallel Processing

Celery can process **multiple pages simultaneously** if you have multiple workers:

### Single Worker (Sequential):
```
Page 1 → Page 2 → Page 3 → Page 4 → Page 5 → Page 6 → Page 7 → Page 8
Total: ~4 minutes
```

### Multiple Workers (Parallel):
```
Worker 1: Page 1 → Page 5
Worker 2: Page 2 → Page 6
Worker 3: Page 3 → Page 7
Worker 4: Page 4 → Page 8
Total: ~1 minute ⚡
```

**Configure Workers:**
```bash
# In Render or Docker
celery -A backend worker --loglevel=info --concurrency=4
```

---

## 📊 Monitoring in Real-Time

### Check Render Logs:
```
# You'll see these logs in Render dashboard:

[AUDIO GENERATION] Queuing background tasks for 8 pages...
[AUDIO GENERATION] Book ID: 123
[AUDIO TASK] Page 1/8 - Task ID: abc-123 - Status: QUEUED ✓
[AUDIO TASK] Page 2/8 - Task ID: def-456 - Status: QUEUED ✓
...
[🎵 AUDIO TASK] Starting audio generation for Book 123, Page 1
[✅ AUDIO TASK] Page 1 - COMPLETED!
[📊 PROGRESS] Book 123 - 1/8 pages completed (12%)
[✅ AUDIO TASK] Page 2 - COMPLETED!
[📊 PROGRESS] Book 123 - 2/8 pages completed (25%)
...
[🎉 COMPLETE] Book 123 - ALL AUDIO GENERATED! Total duration: 224s
```

---

## 🔄 Complete Flow Diagram

```
┌──────────────────────────────────────────────────────┐
│ 1. User Uploads PDF (SSE Stream)                     │
│    POST /api/books/upload/?stream=true               │
└───────────────────┬──────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ 2. Gemini Extracts Text (~40s for 8 pages)          │
│    - Convert PDF to images                           │
│    - Extract text with Gemini Vision API             │
│    - Create BookPage records                         │
└───────────────────┬──────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ 3. Queue Audio Tasks (Instant)                       │
│    - generate_page_audio.delay(book_id, 1)          │
│    - generate_page_audio.delay(book_id, 2)          │
│    - ... (all pages)                                 │
└───────────────────┬──────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ 4. API Returns 200 OK ✅                             │
│    {                                                  │
│      "book_id": 123,                                 │
│      "status_url": "/api/books/123/status/"          │
│    }                                                  │
└──────────────────────────────────────────────────────┘

        ║ MEANWHILE (Background - Asynchronous)
        ↓
┌──────────────────────────────────────────────────────┐
│ 5. Celery Workers Generate Audio (~30s/page)        │
│    For each page:                                     │
│    - Read text from BookPage                         │
│    - Generate audio with Edge TTS                    │
│    - Upload MP3 to Cloudinary                        │
│    - Update BookPage.processing_status = 'completed' │
│    - Update Book.processing_progress                 │
└───────────────────┬──────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ 6. Check Status Anytime                              │
│    GET /api/books/123/status/                        │
│    {                                                  │
│      "processing_progress": 75,                      │
│      "pages_with_audio": 6,                          │
│      "audio_ready": false                            │
│    }                                                  │
└──────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ 7. All Pages Complete 🎉                             │
│    {                                                  │
│      "processing_status": "completed",               │
│      "processing_progress": 100,                     │
│      "audio_ready": true                             │
│    }                                                  │
└──────────────────────────────────────────────────────┘
```

---

## 🎯 Summary

### Upload API (Synchronous Part):
- ✅ Extracts text with Gemini
- ✅ Creates database records
- ✅ Queues audio tasks
- ⏱️ Returns in ~40 seconds

### Audio Generation (Asynchronous Part):
- 🎵 Happens in background
- 🔄 Processed by Celery workers
- ⏱️ Takes ~30 seconds per page
- 📊 Track with `/api/books/{id}/status/`

### How to Know When Done:
1. **Poll status API** every 5 seconds
2. **Check `audio_ready` field** in response
3. **Watch `processing_progress`** (0-100%)
4. **Monitor Render logs** for completion messages

---

## 🚀 Best Practices

1. **Show Progress Bar**: Use `processing_progress` to show user
2. **Poll Every 5-10s**: Don't spam the status API
3. **Enable Notifications**: Alert user when complete
4. **Handle Failures**: Check `pages_status.failed` count
5. **Provide ETA**: Use `estimated_time_remaining` field

---

**Your upload API is fast (40s), audio generates in background! Users can continue browsing while audio is being created.** 🎉
