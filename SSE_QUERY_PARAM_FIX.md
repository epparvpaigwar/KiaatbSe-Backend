# SSE Query Parameter Fix

## Problem

Getting error: `{"detail":"Could not satisfy the request Accept header."}`

This was caused by Django REST Framework's content negotiation rejecting the `Accept: text/event-stream` header.

---

## Solution

Changed from **Accept header** to **Query parameter**

### Before (Not Working):
```javascript
fetch('/api/books/upload/', {
  headers: {
    'Accept': 'text/event-stream'  // ❌ DRF blocks this
  }
})
```

### After (Working):
```javascript
fetch('/api/books/upload/?stream=true', {  // ✅ Use query param
  // No Accept header needed
})
```

---

## How to Use

### For SSE Real-Time Progress:
```bash
POST /api/books/upload/?stream=true
```

### For Regular JSON Response:
```bash
POST /api/books/upload/
```
(No query parameter)

---

## Examples

### JavaScript/React (SSE Mode):
```javascript
const formData = new FormData();
formData.append('pdf_file', file);
formData.append('title', 'My Book');

fetch('/api/books/upload/?stream=true', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
}).then(response => {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  function read() {
    reader.read().then(({ done, value }) => {
      if (done) return;

      const chunk = decoder.decode(value);
      // Parse SSE events from chunk
      // ...

      read();
    });
  }

  read();
});
```

### JavaScript (Regular Mode):
```javascript
fetch('/api/books/upload/', {  // No ?stream=true
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
}).then(res => res.json())
  .then(data => console.log(data));
```

---

## Testing

### Test SSE Mode:
```bash
curl -N \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "pdf_file=@test.pdf" \
  -F "title=Test Book" \
  "http://localhost:8000/api/books/upload/?stream=true"
```

You should see:
```
event: status
data: {"message": "Authenticating..."}

event: processing_started
data: {"total_pages": 10}

event: page_progress
data: {"current_page": 1, "total_pages": 10, "progress": 10}
...
```

### Test Regular Mode:
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "pdf_file=@test.pdf" \
  -F "title=Test Book" \
  "http://localhost:8000/api/books/upload/"
```

You should see:
```json
{
  "data": {
    "id": 123,
    "title": "Test Book",
    "total_pages": 10
  },
  "status": "PASS"
}
```

---

## Changes Made

### 1. `audiobooks/views.py`
Changed from:
```python
accept_header = request.META.get('HTTP_ACCEPT', '')
use_sse = 'text/event-stream' in accept_header
```

To:
```python
use_sse = request.query_params.get('stream', '').lower() == 'true'
```

### 2. Updated Documentation
- SSE_UPLOAD_API_DOCUMENTATION.md
- All examples now use `?stream=true`
- Removed Accept header requirement

---

## Summary

✅ **Fixed:** DRF Accept header issue
✅ **Solution:** Use query parameter `?stream=true`
✅ **Backward Compatible:** Works with both modes
✅ **Simpler:** No special headers needed

**Payload stays the same - only response format changes!**
