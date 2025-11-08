# SSE (Server-Sent Events) Upload API Documentation

## Overview

This API uses **Server-Sent Events (SSE)** to provide real-time progress updates during PDF upload and OCR processing.

Instead of waiting for the entire process to complete, the frontend receives continuous updates like:
- "Uploading file..."
- "Processing page 1 of 10..."
- "Processing page 2 of 10..."
- "Completed!"

---

## API Endpoint

### Upload Book with SSE Progress

**Endpoint:** `POST /api/books/upload/?stream=true`

**Method:** `POST`

**Content-Type:** `multipart/form-data`

**Response Type:** `text/event-stream` (SSE)

**Authentication:** Bearer Token Required

**Query Parameters:**
- `stream=true` - Enable SSE real-time progress (optional)
- If omitted or `stream=false` - Returns regular JSON response

---

## Request Format

### Headers
```http
Authorization: Bearer <your_jwt_token>
Content-Type: multipart/form-data
```

### Query Parameters
```
stream=true
```

### Body (Form Data)
```javascript
{
  "file": <PDF file>,
  "title": "Book Title",
  "author": "Author Name",
  "language": "hindi",  // or "english" or "hinglish"
  "category": "fiction",
  "description": "Book description (optional)"
}
```

---

## Response Format (SSE)

SSE responses are sent as a stream of events in this format:

```
event: <event_type>
data: <json_data>

```

### Event Types

#### 1. `status` - General status updates
```javascript
event: status
data: {"message": "Starting upload..."}
```

#### 2. `upload_progress` - File upload progress
```javascript
event: upload_progress
data: {"progress": 45, "message": "Uploading... 45%"}
```

#### 3. `processing_started` - OCR processing started
```javascript
event: processing_started
data: {"total_pages": 10, "message": "Processing 10 pages with OCR"}
```

#### 4. `page_progress` - Individual page OCR progress
```javascript
event: page_progress
data: {
  "current_page": 3,
  "total_pages": 10,
  "progress": 30,
  "message": "Processing page 3 of 10",
  "extracted_chars": 1234
}
```

#### 5. `completed` - Processing completed successfully
```javascript
event: completed
data: {
  "book_id": 123,
  "title": "Book Title",
  "total_pages": 10,
  "message": "Upload completed successfully!"
}
```

#### 6. `error` - Error occurred
```javascript
event: error
data: {
  "error": "OCR processing failed",
  "details": "Tesseract timeout on page 5"
}
```

---

## Frontend Implementation

### JavaScript (Vanilla)

```javascript
async function uploadBookWithProgress(file, metadata) {
  const formData = new FormData();
  formData.append('pdf_file', file);
  formData.append('title', metadata.title);
  formData.append('author', metadata.author);
  formData.append('language', metadata.language);
  formData.append('genre', metadata.genre);

  // Get auth token
  const token = localStorage.getItem('access_token');

  // Upload file with streaming (using fetch with ReadableStream)
  const response = await fetch('/api/books/upload/?stream=true', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  });

  // Read SSE stream
  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  // Function to read and process SSE stream
  function processStream() {
    reader.read().then(({ done, value }) => {
      if (done) {
        console.log('Stream complete');
        return;
      }

      // Decode the chunk
      const chunk = decoder.decode(value);
      const events = chunk.split('\n\n').filter(e => e.trim());

      events.forEach(eventText => {
        const lines = eventText.split('\n');
        let eventType = '';
        let data = null;

        lines.forEach(line => {
          if (line.startsWith('event:')) {
            eventType = line.substring(7).trim();
          } else if (line.startsWith('data:')) {
            data = JSON.parse(line.substring(6));
          }
        });

        // Handle events
        if (eventType === 'status') {
          console.log('Status:', data.message);
          updateUI(data.message);
        } else if (eventType === 'processing_started') {
          console.log('Processing started:', data.total_pages, 'pages');
          showProcessingUI(data.total_pages);
        } else if (eventType === 'page_progress') {
          console.log(`Page ${data.current_page}/${data.total_pages}`);
          updatePageProgress(data.current_page, data.total_pages);
        } else if (eventType === 'completed') {
          console.log('Completed!', data);
          showSuccess(data);
          return;
        } else if (eventType === 'error') {
          console.error('Error:', data.error);
          showError(data.error);
          return;
        }
      });

      // Continue reading
      processStream();
    });
  }

  processStream();
}

// Helper functions
function updateUI(message) {
  document.getElementById('status-message').textContent = message;
}

function updateProgressBar(progress) {
  document.getElementById('progress-bar').style.width = progress + '%';
  document.getElementById('progress-text').textContent = progress + '%';
}

function updatePageProgress(current, total) {
  const progress = Math.round((current / total) * 100);
  document.getElementById('page-info').textContent =
    `Processing page ${current} of ${total}`;
  updateProgressBar(progress);
}

function showSuccess(data) {
  alert(`Book uploaded successfully! ID: ${data.book_id}`);
  window.location.href = `/books/${data.book_id}`;
}

function showError(error) {
  alert('Error: ' + error);
}
```

### React Implementation

```jsx
import { useState } from 'react';

function BookUploadWithSSE() {
  const [status, setStatus] = useState('');
  const [progress, setProgress] = useState(0);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  const uploadBook = async (file, metadata) => {
    const formData = new FormData();
    formData.append('pdf_file', file);
    formData.append('title', metadata.title);
    formData.append('author', metadata.author);
    formData.append('language', metadata.language);

    const token = localStorage.getItem('access_token');

    // Upload with streaming
    const response = await fetch('http://localhost:8000/api/books/upload/?stream=true', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    // Read stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    const processStream = async () => {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const events = chunk.split('\n\n').filter(e => e.trim());

        events.forEach(eventText => {
          const lines = eventText.split('\n');
          let eventType = '';
          let data = null;

          lines.forEach(line => {
            if (line.startsWith('event:')) {
              eventType = line.substring(7).trim();
            } else if (line.startsWith('data:')) {
              data = JSON.parse(line.substring(6));
            }
          });

          if (eventType === 'status') {
            setStatus(data.message);
          } else if (eventType === 'processing_started') {
            setTotalPages(data.total_pages);
            setStatus(data.message);
          } else if (eventType === 'page_progress') {
            setCurrentPage(data.current_page);
            setTotalPages(data.total_pages);
            setProgress(data.progress);
            setStatus(data.message);
          } else if (eventType === 'completed') {
            setStatus('Upload completed!');
            setProgress(100);
          } else if (eventType === 'error') {
            setStatus('Error: ' + data.error);
          }
        });
      }
    };

    processStream();
  };

  return (
    <div>
      <h2>Upload Book</h2>
      <div className="status">{status}</div>
      <div className="progress-bar">
        <div style={{ width: `${progress}%` }}>{progress}%</div>
      </div>
      {totalPages > 0 && (
        <div>Processing page {currentPage} of {totalPages}</div>
      )}
    </div>
  );
}
```

### Vue.js Implementation

```vue
<template>
  <div class="upload-container">
    <h2>Upload Book</h2>
    <div class="status">{{ status }}</div>
    <div class="progress-bar">
      <div :style="{ width: progress + '%' }">{{ progress }}%</div>
    </div>
    <div v-if="totalPages > 0">
      Processing page {{ currentPage }} of {{ totalPages }}
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      status: '',
      progress: 0,
      currentPage: 0,
      totalPages: 0,
      eventSource: null,
    };
  },
  methods: {
    async uploadBook(file, metadata) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', metadata.title);
      formData.append('author', metadata.author);

      const token = localStorage.getItem('access_token');

      // Create SSE connection
      this.eventSource = new EventSource(
        `http://localhost:8000/api/books/upload-sse/?token=${token}`
      );

      this.eventSource.addEventListener('status', (event) => {
        const data = JSON.parse(event.data);
        this.status = data.message;
      });

      this.eventSource.addEventListener('page_progress', (event) => {
        const data = JSON.parse(event.data);
        this.currentPage = data.current_page;
        this.totalPages = data.total_pages;
        this.progress = data.progress;
        this.status = data.message;
      });

      this.eventSource.addEventListener('completed', (event) => {
        this.status = 'Upload completed!';
        this.progress = 100;
        this.eventSource.close();
      });

      this.eventSource.addEventListener('error', (event) => {
        const data = JSON.parse(event.data);
        this.status = 'Error: ' + data.error;
        this.eventSource.close();
      });

      // Upload file
      await fetch('http://localhost:8000/api/books/upload-sse/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });
    },
  },
  beforeUnmount() {
    if (this.eventSource) {
      this.eventSource.close();
    }
  },
};
</script>
```

---

## Complete Event Flow

### Timeline of Events

```
1. User uploads file
   ↓
2. event: status
   data: {"message": "Validating file..."}
   ↓
3. event: status
   data: {"message": "File uploaded successfully"}
   ↓
4. event: processing_started
   data: {"total_pages": 10, "message": "Processing 10 pages with OCR"}
   ↓
5. event: page_progress
   data: {"current_page": 1, "total_pages": 10, "progress": 10, "message": "Processing page 1 of 10"}
   ↓
6. event: page_progress
   data: {"current_page": 2, "total_pages": 10, "progress": 20, "message": "Processing page 2 of 10"}
   ↓
   ... (continues for each page) ...
   ↓
10. event: page_progress
    data: {"current_page": 10, "total_pages": 10, "progress": 100, "message": "Processing page 10 of 10"}
    ↓
11. event: completed
    data: {"book_id": 123, "title": "My Book", "total_pages": 10, "message": "Upload completed!"}
```

---

## Error Handling

### Common Errors

1. **File too large**
```javascript
event: error
data: {"error": "File size exceeds limit", "details": "Max size: 50MB"}
```

2. **Invalid file type**
```javascript
event: error
data: {"error": "Invalid file type", "details": "Only PDF files allowed"}
```

3. **OCR timeout**
```javascript
event: error
data: {"error": "OCR processing timeout", "details": "Page 5 took too long"}
```

4. **Authentication failed**
```javascript
event: error
data: {"error": "Unauthorized", "details": "Invalid or expired token"}
```

---

## UI/UX Recommendations

### 1. Progress Bar
Show a visual progress bar that updates with each page:
```html
<div class="progress-container">
  <div class="progress-bar" id="progress-bar"></div>
  <span id="progress-text">0%</span>
</div>
```

### 2. Status Messages
Display current operation:
```html
<div class="status-message" id="status-message">
  Starting upload...
</div>
```

### 3. Page Counter
Show which page is being processed:
```html
<div class="page-counter">
  Processing page <span id="current-page">0</span>
  of <span id="total-pages">0</span>
</div>
```

### 4. Cancel Button
Allow users to cancel the upload:
```html
<button onclick="cancelUpload()">Cancel Upload</button>
```

```javascript
function cancelUpload() {
  eventSource.close();
  // Optionally call API to cleanup
  fetch('/api/books/cancel-upload/', {
    method: 'POST',
    headers: {'Authorization': `Bearer ${token}`},
  });
}
```

---

## Testing

### Using cURL (SSE Test)
```bash
curl -N \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "pdf_file=@test.pdf" \
  -F "title=Test Book" \
  -F "author=Test Author" \
  "http://localhost:8000/api/books/upload/?stream=true"
```

### Using cURL (Regular JSON Test)
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "pdf_file=@test.pdf" \
  -F "title=Test Book" \
  "http://localhost:8000/api/books/upload/"
```

---

## Benefits of SSE

✅ **Real-time feedback** - Users see progress instantly
✅ **Better UX** - No more "loading..." for minutes
✅ **Transparency** - Users know what's happening
✅ **Error visibility** - Instant error notifications
✅ **Simple protocol** - Easier than WebSockets
✅ **One-way communication** - Perfect for progress updates

---

## Comparison: Regular vs SSE

### Regular API (Before)
```
User uploads PDF → Wait 3 minutes → Get result or timeout
```
**Problems:**
- No feedback during processing
- Users don't know if it's working
- Looks like app is frozen

### SSE API (After)
```
User uploads PDF →
  "Uploading..." →
  "Processing page 1/10..." →
  "Processing page 2/10..." →
  ... →
  "Completed!"
```
**Benefits:**
- Continuous feedback
- Progress visibility
- Better user experience

---

## Next Steps

1. **Backend:** Implement SSE endpoint (I'll create this for you)
2. **Frontend:** Integrate EventSource as shown above
3. **Testing:** Test with various PDF sizes
4. **UI/UX:** Design progress indicators

Would you like me to create the backend SSE implementation now?
