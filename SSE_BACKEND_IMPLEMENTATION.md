# SSE Backend Implementation Guide

## Overview

This guide shows how to implement Server-Sent Events (SSE) for the book upload API in Django.

---

## Step 1: Create SSE Utility

Create a helper for SSE responses:

### File: `audiobooks/utils/sse.py`

```python
"""
Server-Sent Events (SSE) Utilities
"""
import json
from django.http import StreamingHttpResponse


class SSEResponse:
    """Helper class for Server-Sent Events responses"""

    @staticmethod
    def format_event(event_type, data):
        """
        Format data as SSE event

        Args:
            event_type: Type of event (status, progress, error, etc.)
            data: Dictionary of data to send

        Returns:
            Formatted SSE string
        """
        json_data = json.dumps(data)
        return f"event: {event_type}\ndata: {json_data}\n\n"

    @staticmethod
    def create_response(generator):
        """
        Create StreamingHttpResponse for SSE

        Args:
            generator: Generator function that yields SSE events

        Returns:
            StreamingHttpResponse with proper headers
        """
        response = StreamingHttpResponse(
            generator,
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
        return response


def send_sse_event(event_type, data):
    """
    Send a single SSE event

    Args:
        event_type: Type of event
        data: Data dictionary

    Returns:
        Formatted SSE event string
    """
    return SSEResponse.format_event(event_type, data)
```

---

## Step 2: Modify PDFProcessorOCR to Support Progress Callbacks

### File: `audiobooks/services/pdf_processor_ocr.py`

Add callback support:

```python
@staticmethod
def extract_pages_with_ocr(pdf_file_path, use_ocr=True, language='hin+eng', progress_callback=None):
    """
    Extract text from all pages of a PDF file using OCR

    Args:
        pdf_file_path: Path to PDF file
        use_ocr: Use OCR (True) or simple text extraction (False)
        language: Tesseract language code (default: 'hin+eng')
        progress_callback: Optional callback function for progress updates
                          Called with (current_page, total_pages, text_length)

    Returns:
        dict: {
            'success': bool,
            'total_pages': int,
            'pages': [{'page_number': int, 'text': str}, ...],
            'error': str (if any)
        }
    """
    try:
        pages_data = []

        # First, get total page count
        with pdfplumber.open(pdf_file_path) as pdf:
            total_pages = len(pdf.pages)

        logger.info(f"Processing {total_pages} pages with OCR (lang={language})")

        # Send initial progress callback
        if progress_callback:
            progress_callback(0, total_pages, 0)

        if use_ocr:
            # Convert PDF pages to images for OCR
            logger.info("Converting PDF to images...")
            images = convert_from_path(
                pdf_file_path,
                dpi=150,
                fmt='jpeg'
            )

            logger.info(f"Processing {len(images)} images with Tesseract OCR")

            # Process each image with OCR
            for page_num, image in enumerate(images, start=1):
                try:
                    # Extract text using Tesseract
                    text = pytesseract.image_to_string(
                        image,
                        lang=language,
                        config='--psm 6'
                    )

                    # Clean text
                    text = PDFProcessorOCR._clean_text(text)

                    pages_data.append({
                        'page_number': page_num,
                        'text': text
                    })

                    logger.info(f"OCR extracted page {page_num}/{total_pages} ({len(text)} chars)")

                    # Send progress callback
                    if progress_callback:
                        progress_callback(page_num, total_pages, len(text))

                except Exception as e:
                    logger.error(f"OCR error on page {page_num}: {str(e)}")
                    pages_data.append({
                        'page_number': page_num,
                        'text': ""
                    })

                    # Still send progress callback even on error
                    if progress_callback:
                        progress_callback(page_num, total_pages, 0)

        else:
            # Fallback to simple text extraction (pdfplumber)
            with pdfplumber.open(pdf_file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        text = page.extract_text() or ""
                        text = PDFProcessorOCR._clean_text(text)

                        pages_data.append({
                            'page_number': page_num,
                            'text': text
                        })

                        logger.info(f"Extracted page {page_num}/{total_pages}")

                        # Send progress callback
                        if progress_callback:
                            progress_callback(page_num, total_pages, len(text))

                    except Exception as e:
                        logger.error(f"Error extracting page {page_num}: {str(e)}")
                        pages_data.append({
                            'page_number': page_num,
                            'text': ""
                        })

        return {
            'success': True,
            'total_pages': total_pages,
            'pages': pages_data,
            'error': None
        }

    except Exception as e:
        logger.error(f"PDF extraction failed: {str(e)}")
        return {
            'success': False,
            'total_pages': 0,
            'pages': [],
            'error': str(e)
        }
```

---

## Step 3: Create SSE Upload View

### File: `audiobooks/views.py`

Add new SSE upload endpoint:

```python
from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .utils.sse import send_sse_event
import time


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_book_sse(request):
    """
    Upload book with Server-Sent Events progress updates

    Returns SSE stream with real-time progress
    """
    def event_stream():
        try:
            # Send initial status
            yield send_sse_event('status', {
                'message': 'Validating file...'
            })

            # Validate file
            if 'file' not in request.FILES:
                yield send_sse_event('error', {
                    'error': 'No file provided',
                    'details': 'Please upload a PDF file'
                })
                return

            file = request.FILES['file']

            # Validate file type
            if not file.name.endswith('.pdf'):
                yield send_sse_event('error', {
                    'error': 'Invalid file type',
                    'details': 'Only PDF files are allowed'
                })
                return

            # Validate file size (50MB limit)
            if file.size > 50 * 1024 * 1024:
                yield send_sse_event('error', {
                    'error': 'File too large',
                    'details': 'Maximum file size is 50MB'
                })
                return

            # Send upload status
            yield send_sse_event('status', {
                'message': 'File validated successfully'
            })

            # Save file temporarily
            import tempfile
            import os

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            for chunk in file.chunks():
                temp_file.write(chunk)
            temp_file.close()

            yield send_sse_event('status', {
                'message': 'File uploaded, starting OCR processing...'
            })

            # Get metadata
            title = request.POST.get('title', file.name)
            author = request.POST.get('author', 'Unknown')
            language = request.POST.get('language', 'hindi')
            category = request.POST.get('category', 'general')
            description = request.POST.get('description', '')

            # Determine OCR language
            lang_map = {
                'hindi': 'hin+eng',
                'english': 'eng',
                'hinglish': 'hin+eng'
            }
            ocr_language = lang_map.get(language, 'hin+eng')

            # Progress callback for OCR
            def progress_callback(current_page, total_pages, chars_extracted):
                progress_percent = int((current_page / total_pages) * 100)

                event_data = {
                    'current_page': current_page,
                    'total_pages': total_pages,
                    'progress': progress_percent,
                    'message': f'Processing page {current_page} of {total_pages}',
                    'extracted_chars': chars_extracted
                }

                # Send page progress event (non-blocking)
                return send_sse_event('page_progress', event_data)

            # Send processing started event
            # First, get page count
            import pdfplumber
            with pdfplumber.open(temp_file.name) as pdf:
                total_pages = len(pdf.pages)

            yield send_sse_event('processing_started', {
                'total_pages': total_pages,
                'message': f'Processing {total_pages} pages with OCR'
            })

            # Process PDF with OCR and progress updates
            from .services.pdf_processor_ocr import PDFProcessorOCR

            # Store progress events to yield
            progress_events = []

            def callback_wrapper(current, total, chars):
                progress_events.append(
                    progress_callback(current, total, chars)
                )

            # Extract pages (this will call our callback)
            result = PDFProcessorOCR.extract_pages_with_ocr(
                temp_file.name,
                use_ocr=True,
                language=ocr_language,
                progress_callback=callback_wrapper
            )

            # Yield all progress events
            for event in progress_events:
                yield event
                time.sleep(0.1)  # Small delay to ensure events are sent

            # Clean up temp file
            os.unlink(temp_file.name)

            # Check if processing was successful
            if not result['success']:
                yield send_sse_event('error', {
                    'error': 'OCR processing failed',
                    'details': result.get('error', 'Unknown error')
                })
                return

            # Create book object
            from .models import Book
            book = Book.objects.create(
                user=request.user,
                title=title,
                author=author,
                language=language,
                category=category,
                description=description,
                total_pages=result['total_pages'],
                pdf_url=file.name,  # Save to Cloudinary separately
            )

            # Save pages
            from .models import BookPage
            for page_data in result['pages']:
                BookPage.objects.create(
                    book=book,
                    page_number=page_data['page_number'],
                    text_content=page_data['text']
                )

            # Send completion event
            yield send_sse_event('completed', {
                'book_id': book.id,
                'title': book.title,
                'author': book.author,
                'total_pages': book.total_pages,
                'message': 'Upload completed successfully!'
            })

        except Exception as e:
            import traceback
            logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
            yield send_sse_event('error', {
                'error': 'Upload failed',
                'details': str(e)
            })

    # Return SSE response
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
```

---

## Step 4: Add URL Route

### File: `audiobooks/urls.py`

```python
from django.urls import path
from . import views

urlpatterns = [
    # ... existing routes ...

    # SSE upload endpoint
    path('books/upload-sse/', views.upload_book_sse, name='upload-book-sse'),
]
```

---

## Step 5: Update CORS Settings

### File: `backend/settings.py`

Ensure SSE works with CORS:

```python
CORS_ALLOW_HEADERS = list(default_headers) + [
    'cache-control',
    'x-accel-buffering',
]
```

---

## Testing the SSE Endpoint

### Using cURL

```bash
curl -N -H "Accept: text/event-stream" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.pdf" \
  -F "title=Test Book" \
  -F "author=Test Author" \
  http://localhost:8000/api/books/upload-sse/
```

### Using Python

```python
import requests

url = 'http://localhost:8000/api/books/upload-sse/'
headers = {
    'Authorization': 'Bearer YOUR_TOKEN',
}
files = {
    'file': open('test.pdf', 'rb'),
}
data = {
    'title': 'Test Book',
    'author': 'Test Author',
    'language': 'hindi',
}

response = requests.post(url, headers=headers, files=files, data=data, stream=True)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

---

## Important Notes

### 1. Nginx Configuration (If using Nginx)

Add to nginx config to prevent buffering:

```nginx
location /api/books/upload-sse/ {
    proxy_pass http://backend;
    proxy_buffering off;
    proxy_cache off;
    proxy_set_header X-Accel-Buffering no;
    proxy_read_timeout 600s;
}
```

### 2. Gunicorn Workers

Use async workers for better SSE performance:

```bash
gunicorn backend.wsgi:application \
  --worker-class gevent \
  --workers 2 \
  --timeout 600
```

Or install gevent:
```bash
pip install gevent
```

### 3. Render Configuration

For Render, update Dockerfile:

```dockerfile
# Install gevent for async SSE
RUN pip install gevent

# Run with gevent worker
CMD gunicorn backend.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --timeout 300 \
    --worker-class gevent \
    --workers 2
```

---

## Alternative: Simpler Implementation (Without Gevent)

If you don't want to use gevent, you can yield events differently:

```python
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_book_sse_simple(request):
    """Simplified SSE upload without gevent"""

    def event_stream():
        # Send status
        yield send_sse_event('status', {'message': 'Starting...'})

        # Process file
        # ... your processing code ...

        # Yield progress manually
        for i in range(1, total_pages + 1):
            yield send_sse_event('page_progress', {
                'current_page': i,
                'total_pages': total_pages,
                'progress': int((i / total_pages) * 100),
            })

        yield send_sse_event('completed', {'message': 'Done!'})

    return StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
```

---

## Summary

1. ✅ Created SSE utility (`sse.py`)
2. ✅ Modified PDFProcessorOCR with callbacks
3. ✅ Created SSE upload view
4. ✅ Added URL route
5. ✅ Configured CORS for SSE

**Next:** Implement frontend using the documentation in `SSE_UPLOAD_API_DOCUMENTATION.md`!
