"""
Audiobook API Views
Handles book upload, listing, playback, progress tracking, and library management
"""
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse
import json
import logging

from users.utils import APIResponse, get_user_from_token
from .models import Book, BookPage, ListeningProgress, UserLibrary
from .serializers import (
    BookListSerializer, BookDetailSerializer, BookUploadSerializer,
    BookPageSerializer, ListeningProgressSerializer, UserLibrarySerializer,
    ProgressUpdateSerializer
)
from .tasks import process_book_pdf

logger = logging.getLogger(__name__)


def send_sse_event(event_type, data):
    """Helper function to format SSE events"""
    json_data = json.dumps(data)
    return f"event: {event_type}\ndata: {json_data}\n\n"


@method_decorator(csrf_exempt, name='dispatch')
class BookUploadView(APIView):
    """
    API to upload a book PDF with real-time SSE progress updates

    Headers:
    Authorization: Bearer <token>

    Query Parameters:
    - stream=true (for SSE real-time progress)
    - stream=false or omit (for regular JSON response)

    Payload (multipart/form-data):
    {
        "title": "Book Title",
        "author": "Author Name",
        "description": "Book description",
        "language": "hindi",
        "genre": "literature",
        "pdf_file": <PDF file>,
        "cover_image": <Image file> (optional),
        "is_public": true
    }

    SSE Events (when stream=true):
    - event: status - General status updates
    - event: upload_progress - File upload progress
    - event: processing_started - Text extraction processing started
    - event: page_progress - Individual page extraction progress
    - event: audio_generation_started - Audio generation started
    - event: completed - Processing completed
    - event: error - Error occurred

    Regular Response (when stream=false or omitted):
    {
        "data": {
            "id": 1,
            "title": "Book Title",
            "processing_status": "uploaded",
            "message": "Book uploaded successfully. Processing started."
        },
        "status": "PASS",
        "http_code": 201,
        "message": "Book uploaded successfully"
    }

    Examples:
    - SSE mode: POST /api/books/upload/?stream=true
    - Regular mode: POST /api/books/upload/

    Notes:
    - Requires authentication
    - PDF max size: 50MB
    - Cover image max size: 5MB
    - Use ?stream=true for real-time progress updates
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Always use SSE streaming for real-time progress updates
        # Non-SSE mode removed as SSE provides better user experience
        return self._post_with_sse(request)

    def _post_with_sse(self, request):
        """Handle upload with Server-Sent Events for real-time progress"""

        # PRE-PROCESS: Read file and metadata BEFORE starting SSE stream
        # This prevents "Connection reset by peer" errors
        import tempfile
        import os

        try:
            # Authenticate user first
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            # Return error as SSE
            def error_stream():
                yield send_sse_event('error', {
                    'error': 'Authentication failed',
                    'details': str(e)
                })
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        # Validate and read file
        pdf_file = request.FILES.get('pdf_file')
        if not pdf_file:
            def error_stream():
                yield send_sse_event('error', {
                    'error': 'No file provided',
                    'details': 'Please upload a PDF file'
                })
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        # Validate file type
        if not pdf_file.name.endswith('.pdf'):
            def error_stream():
                yield send_sse_event('error', {
                    'error': 'Invalid file type',
                    'details': 'Only PDF files are allowed'
                })
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        # Validate file size (50MB limit)
        if pdf_file.size > 50 * 1024 * 1024:
            def error_stream():
                yield send_sse_event('error', {
                    'error': 'File too large',
                    'details': 'Maximum file size is 50MB'
                })
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        # Get metadata from request
        title = request.POST.get('title', pdf_file.name)
        author = request.POST.get('author', 'Unknown')
        language = request.POST.get('language', 'hindi')
        genre = request.POST.get('genre', 'literature')
        description = request.POST.get('description', '')
        is_public = request.POST.get('is_public', 'true').lower() == 'true'

        # Get cover image if provided
        cover_image = request.FILES.get('cover_image')

        # Save file to temp location BEFORE streaming
        try:
            temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            for chunk in pdf_file.chunks():
                temp_pdf.write(chunk)
            temp_pdf.close()
            temp_pdf_path = temp_pdf.name
            print(f"[UPLOAD DEBUG] File saved to temp: {temp_pdf_path}")
        except Exception as e:
            def error_stream():
                yield send_sse_event('error', {
                    'error': 'File upload failed',
                    'details': str(e)
                })
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        # NOW start the SSE stream with processing
        def event_stream():
            try:
                yield send_sse_event('status', {'message': 'Authentication successful'})
                yield send_sse_event('status', {'message': 'File validated successfully'})
                yield send_sse_event('status', {
                    'message': 'File uploaded successfully. Starting text extraction...'
                })

                # Determine OCR language
                lang_map = {
                    'hindi': 'hin+eng',
                    'english': 'eng',
                    'hinglish': 'hin+eng'
                }
                ocr_language = lang_map.get(language, 'hin+eng')

                # Get total pages first
                import pdfplumber
                with pdfplumber.open(temp_pdf_path) as pdf:
                    total_pages = len(pdf.pages)

                yield send_sse_event('processing_started', {
                    'total_pages': total_pages,
                    'message': f'Processing {total_pages} pages...'
                })

                print(f"\n{'='*60}")
                print(f"[UPLOAD DEBUG] Starting OCR processing for {total_pages} pages")
                print(f"[UPLOAD DEBUG] OCR Language: {ocr_language}")
                print(f"[UPLOAD DEBUG] Temp file: {temp_pdf_path}")
                print(f"{'='*60}\n")

                # Progress callback for Gemini extraction
                progress_events = []

                def progress_callback(current_page, total, chars_extracted):
                    print(f"[PROGRESS CALLBACK] Page {current_page}/{total} - Chars: {chars_extracted}")
                    progress_percent = int((current_page / total) * 100)
                    event_data = {
                        'current_page': current_page,
                        'total_pages': total,
                        'progress': progress_percent,
                        'message': f'Processing page {current_page} of {total}',
                        'extracted_chars': chars_extracted
                    }
                    progress_events.append(send_sse_event('page_progress', event_data))
                    print(f"[PROGRESS CALLBACK] Event added to queue. Total events: {len(progress_events)}")

                # Process PDF with Gemini Vision API
                from .services.pdf_processor_gemini import PDFProcessorGemini

                print(f"[UPLOAD DEBUG] About to call PDFProcessorGemini.extract_pages_with_gemini...")

                # Map language to Gemini format
                gemini_language = 'hindi' if 'hin' in ocr_language else 'english'

                result = PDFProcessorGemini.extract_pages_with_gemini(
                    temp_pdf_path,
                    language=gemini_language,
                    progress_callback=progress_callback
                )

                print(f"[UPLOAD DEBUG] Gemini processing completed!")
                print(f"[UPLOAD DEBUG] Result success: {result.get('success', False)}")
                print(f"[UPLOAD DEBUG] Total progress events collected: {len(progress_events)}")
                print(f"[UPLOAD DEBUG] Pages extracted: {len(result.get('pages', []))}")

                # Yield all progress events
                print(f"[UPLOAD DEBUG] Now yielding {len(progress_events)} progress events...")
                for i, event in enumerate(progress_events):
                    print(f"[UPLOAD DEBUG] Yielding event {i+1}/{len(progress_events)}")
                    yield event

                # Clean up temp file
                print(f"[UPLOAD DEBUG] Cleaning up temp file...")
                os.unlink(temp_pdf_path)
                print(f"[UPLOAD DEBUG] Temp file deleted")

                # Check if processing was successful
                if not result['success']:
                    print(f"[UPLOAD DEBUG] GEMINI EXTRACTION FAILED! Error: {result.get('error', 'Unknown error')}")
                    yield send_sse_event('error', {
                        'error': 'Text extraction failed',
                        'details': result.get('error', 'Unknown error')
                    })
                    return

                print(f"[UPLOAD DEBUG] Gemini extraction successful! Creating book record...")
                yield send_sse_event('status', {
                    'message': 'Text extraction completed. Creating book record...'
                })

                # Create book object
                book = Book.objects.create(
                    uploader=user,
                    title=title,
                    author=author,
                    language=language,
                    genre=genre,
                    description=description,
                    is_public=is_public,
                    total_pages=result['total_pages'],
                    processing_status='processing'
                )
                print(f"[UPLOAD DEBUG] Book created with ID: {book.id}")

                # Save PDF to Cloudinary
                print(f"[UPLOAD DEBUG] Saving PDF to Cloudinary...")
                book.pdf_file = pdf_file

                # Save cover image if provided
                if cover_image:
                    print(f"[UPLOAD DEBUG] Saving cover image to Cloudinary...")
                    book.cover_image = cover_image

                book.save()
                print(f"[UPLOAD DEBUG] PDF and cover image saved to Cloudinary")

                # Create BookPage records
                yield send_sse_event('status', {
                    'message': f'Creating {result["total_pages"]} page records...'
                })

                print(f"[UPLOAD DEBUG] Creating {len(result['pages'])} BookPage records...")
                for page_data in result['pages']:
                    BookPage.objects.create(
                        book=book,
                        page_number=page_data['page_number'],
                        text_content=page_data['text'],
                        processing_status='pending'
                    )
                print(f"[UPLOAD DEBUG] All BookPage records created")

                # Trigger audio generation (ASYNC - happens in background)
                yield send_sse_event('audio_generation_started', {
                    'message': f'Queuing audio generation for {result["total_pages"]} pages',
                    'total_pages': result['total_pages'],
                    'book_id': book.id
                })

                print(f"\n{'='*60}")
                print(f"[AUDIO GENERATION] Queuing background tasks for {result['total_pages']} pages...")
                print(f"[AUDIO GENERATION] Book ID: {book.id}")
                print(f"{'='*60}")

                from .tasks import generate_page_audio
                for page_num in range(1, result['total_pages'] + 1):
                    task = generate_page_audio.delay(book.id, page_num)
                    print(f"[AUDIO TASK] Page {page_num}/{result['total_pages']} - Task ID: {task.id} - Status: QUEUED ✓")

                print(f"[AUDIO GENERATION] All {result['total_pages']} tasks queued successfully!")
                print(f"[AUDIO GENERATION] Audio will generate in BACKGROUND (asynchronous)")
                print(f"[AUDIO GENERATION] Check status at: /api/books/{book.id}/status/")
                print(f"{'='*60}\n")

                # Send completion event
                print(f"[UPLOAD DEBUG] Sending completion event...")
                yield send_sse_event('completed', {
                    'book_id': book.id,
                    'title': book.title,
                    'author': book.author,
                    'total_pages': book.total_pages,
                    'status_url': f'/api/books/{book.id}/status/',
                    'message': 'Upload completed! Audio generation is running in background. Check status endpoint for progress.'
                })
                print(f"[UPLOAD DEBUG] Upload process completed successfully!")
                print(f"[UPLOAD DEBUG] Monitor audio progress: GET /api/books/{book.id}/status/")

            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                print(f"\n{'='*60}")
                print(f"[UPLOAD ERROR] An exception occurred!")
                print(f"[UPLOAD ERROR] Error: {str(e)}")
                print(f"[UPLOAD ERROR] Traceback:\n{error_trace}")
                print(f"{'='*60}\n")
                logger.error(f"Upload error: {str(e)}\n{error_trace}")

                # Clean up temp file on error
                try:
                    if os.path.exists(temp_pdf_path):
                        os.unlink(temp_pdf_path)
                        print(f"[UPLOAD ERROR] Cleaned up temp file")
                except:
                    pass

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


class BookListView(APIView):
    """
    API to list all public books with filters and search

    Query Parameters:
    - page: Page number (default: 1)
    - search: Search in title/author
    - language: Filter by language (hindi, english, etc.)
    - genre: Filter by genre
    - status: Filter by processing_status (completed, processing, etc.)

    Response:
    {
        "data": {
            "count": 100,
            "next": "http://api.com/books/?page=2",
            "previous": null,
            "results": [
                {
                    "id": 1,
                    "title": "Book Title",
                    "author": "Author Name",
                    "language": "hindi",
                    "total_pages": 150,
                    "processing_status": "completed",
                    ...
                }
            ]
        },
        "status": "PASS",
        "http_code": 200,
        "message": "Books retrieved successfully"
    }
    """

    def get(self, request):
        # Get query parameters
        search_query = request.query_params.get('search', '')
        language = request.query_params.get('language', '')
        genre = request.query_params.get('genre', '')
        processing_status = request.query_params.get('status', '')

        # Base query - only public and active books
        queryset = Book.objects.filter(is_public=True, is_active=True)

        # Apply filters
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(author__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        if language:
            queryset = queryset.filter(language=language)

        if genre:
            queryset = queryset.filter(genre=genre)

        if processing_status:
            queryset = queryset.filter(processing_status=processing_status)

        # Order by latest first
        queryset = queryset.order_by('-uploaded_at')

        # Paginate results (20 per page from settings)
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = BookListSerializer(
                page, many=True, context={'request': request}
            )
            result = paginator.get_paginated_response(serializer.data)

            return APIResponse.success(
                data=result.data,
                message="Books retrieved successfully"
            )

        # If no pagination
        serializer = BookListSerializer(
            queryset, many=True, context={'request': request}
        )
        return APIResponse.success(
            data={"results": serializer.data, "count": queryset.count()},
            message="Books retrieved successfully"
        )


class MyBooksView(APIView):
    """
    API to list user's uploaded books

    Headers:
    Authorization: Bearer <token>

    Query Parameters:
    - status: Filter by processing_status

    Response:
    {
        "data": [
            {
                "id": 1,
                "title": "My Book",
                "processing_status": "completed",
                "processing_progress": 100,
                ...
            }
        ],
        "status": "PASS",
        "http_code": 200,
        "message": "Your books retrieved successfully"
    }
    """

    def get(self, request):
        # Authenticate user
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        # Get user's books
        queryset = Book.objects.filter(uploader=user, is_active=True)

        # Filter by status if provided
        processing_status = request.query_params.get('status', '')
        if processing_status:
            queryset = queryset.filter(processing_status=processing_status)

        # Order by latest first
        queryset = queryset.order_by('-uploaded_at')

        # Serialize
        serializer = BookListSerializer(
            queryset, many=True, context={'request': request}
        )

        return APIResponse.success(
            data=serializer.data,
            message="Your books retrieved successfully"
        )


class BookDetailView(APIView):
    """
    API to get detailed book information

    GET /api/books/<id>/
    - Get book details

    PATCH /api/books/<id>/
    - Update book info (only uploader)

    DELETE /api/books/<id>/
    - Delete book (only uploader)

    Response:
    {
        "data": {
            "id": 1,
            "title": "Book Title",
            "author": "Author",
            "total_pages": 150,
            "pages_count": 150,
            "user_progress": {
                "current_page": 10,
                "completion_percentage": 6
            },
            ...
        },
        "status": "PASS",
        "http_code": 200,
        "message": "Book details retrieved successfully"
    }
    """

    def get(self, request, book_id):
        # Get book
        book = get_object_or_404(Book, id=book_id, is_active=True)

        # Check if book is public or user is uploader
        if not book.is_public:
            try:
                user = get_user_from_token(request)
                if book.uploader != user:
                    return APIResponse.access_denied(
                        message="This book is private"
                    )
            except AuthenticationFailed:
                return APIResponse.access_denied(
                    message="This book is private. Please login."
                )

        # Serialize
        serializer = BookDetailSerializer(book, context={'request': request})

        return APIResponse.success(
            data=serializer.data,
            message="Book details retrieved successfully"
        )

    def patch(self, request, book_id):
        # Authenticate user
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        # Get book
        book = get_object_or_404(Book, id=book_id, is_active=True)

        # Check if user is uploader
        if book.uploader != user:
            return APIResponse.access_denied(
                message="You can only update your own books"
            )

        # Update allowed fields
        allowed_fields = ['title', 'author', 'description', 'genre', 'is_public']
        for field in allowed_fields:
            if field in request.data:
                setattr(book, field, request.data[field])

        book.save()

        # Serialize
        serializer = BookDetailSerializer(book, context={'request': request})

        return APIResponse.success(
            data=serializer.data,
            message="Book updated successfully"
        )

    def delete(self, request, book_id):
        # Authenticate user
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        # Get book
        book = get_object_or_404(Book, id=book_id, is_active=True)

        # Check if user is uploader
        if book.uploader != user:
            return APIResponse.access_denied(
                message="You can only delete your own books"
            )

        # Soft delete
        book.is_active = False
        book.save()

        return APIResponse.success(
            data={"id": book.id},
            message="Book deleted successfully"
        )


class BookPagesView(APIView):
    """
    API to get all pages of a book with audio URLs

    GET /api/books/<id>/pages/

    Query Parameters:
    - page: Page number for pagination

    Response:
    {
        "data": {
            "book": {
                "id": 1,
                "title": "Book Title",
                "total_pages": 150
            },
            "pages": [
                {
                    "id": 1,
                    "page_number": 1,
                    "text_content": "Page text...",
                    "audio_url": "https://cloudinary.com/...",
                    "audio_duration": 45,
                    "processing_status": "completed"
                },
                ...
            ]
        },
        "status": "PASS",
        "http_code": 200,
        "message": "Book pages retrieved successfully"
    }
    """

    def get(self, request, book_id):
        # Get book
        book = get_object_or_404(Book, id=book_id, is_active=True)

        # Check access
        if not book.is_public:
            try:
                user = get_user_from_token(request)
                if book.uploader != user:
                    return APIResponse.access_denied(
                        message="This book is private"
                    )
            except AuthenticationFailed:
                return APIResponse.access_denied(
                    message="This book is private. Please login."
                )

        # Get pages
        pages = BookPage.objects.filter(book=book).order_by('page_number')

        # Serialize
        serializer = BookPageSerializer(pages, many=True)

        return APIResponse.success(
            data={
                "book": {
                    "id": book.id,
                    "title": book.title,
                    "total_pages": book.total_pages,
                    "processing_status": book.processing_status
                },
                "pages": serializer.data
            },
            message="Book pages retrieved successfully"
        )


class BookProcessingStatusView(APIView):
    """
    API to check book processing and audio generation status

    GET /api/books/<id>/status/

    Response:
    {
        "data": {
            "book_id": 1,
            "title": "Book Title",
            "processing_status": "processing",  // uploaded, processing, completed, failed
            "processing_progress": 75,  // 0-100%
            "total_pages": 100,
            "pages_status": {
                "pending": 10,
                "processing": 15,
                "completed": 75,
                "failed": 0
            },
            "audio_ready": false,
            "pages_with_audio": 75,
            "estimated_time_remaining": "5 minutes"
        },
        "status": "PASS",
        "http_code": 200
    }
    """

    def get(self, request, book_id):
        # Get book
        book = get_object_or_404(Book, id=book_id, is_active=True)

        # Count page statuses
        pages = BookPage.objects.filter(book=book)
        total_pages = pages.count()

        pending = pages.filter(processing_status='pending').count()
        processing = pages.filter(processing_status='processing').count()
        completed = pages.filter(processing_status='completed').count()
        failed = pages.filter(processing_status='failed').count()

        # Calculate progress
        progress = int((completed / total_pages) * 100) if total_pages > 0 else 0

        # Estimate time remaining (assuming 30 seconds per page)
        pages_remaining = pending + processing
        estimated_seconds = pages_remaining * 30
        if estimated_seconds < 60:
            estimated_time = f"{estimated_seconds} seconds"
        elif estimated_seconds < 3600:
            estimated_time = f"{int(estimated_seconds / 60)} minutes"
        else:
            estimated_time = f"{int(estimated_seconds / 3600)} hours"

        # Determine overall status
        audio_ready = (completed == total_pages and total_pages > 0)

        return APIResponse.success(
            data={
                "book_id": book.id,
                "title": book.title,
                "processing_status": book.processing_status,
                "processing_progress": progress,
                "total_pages": total_pages,
                "pages_status": {
                    "pending": pending,
                    "processing": processing,
                    "completed": completed,
                    "failed": failed
                },
                "audio_ready": audio_ready,
                "pages_with_audio": completed,
                "estimated_time_remaining": estimated_time if pages_remaining > 0 else "Complete!",
                "created_at": book.uploaded_at,
                "last_updated": book.modified_at
            },
            message="Book processing status retrieved successfully"
        )


class UpdateProgressView(APIView):
    """
    API to update user's listening progress

    Headers:
    Authorization: Bearer <token>

    PUT /api/books/<id>/progress/
    Payload:
    {
        "page_number": 10,
        "position": 30,
        "listened_time": 45
    }

    GET /api/books/<id>/progress/
    - Get current progress

    Response:
    {
        "data": {
            "current_page": 10,
            "current_position": 30,
            "completion_percentage": 6,
            "total_listened_time": 450,
            "is_completed": false
        },
        "status": "PASS",
        "http_code": 200,
        "message": "Progress updated successfully"
    }
    """

    def get(self, request, book_id):
        # Authenticate user
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        # Get book
        book = get_object_or_404(Book, id=book_id, is_active=True)

        # Get or create progress
        progress, created = ListeningProgress.objects.get_or_create(
            user=user,
            book=book
        )

        return APIResponse.success(
            data={
                "current_page": progress.current_page,
                "current_position": progress.current_position,
                "completion_percentage": progress.completion_percentage,
                "total_listened_time": progress.total_listened_time,
                "is_completed": progress.is_completed,
                "last_listened_at": progress.last_listened_at
            },
            message="Progress retrieved successfully"
        )

    def put(self, request, book_id):
        # Authenticate user
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        # Validate input
        serializer = ProgressUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(
                message="Invalid input data",
                errors=serializer.errors
            )

        # Get book
        book = get_object_or_404(Book, id=book_id, is_active=True)

        # Get or create progress
        progress, created = ListeningProgress.objects.get_or_create(
            user=user,
            book=book
        )

        # Update progress
        progress.update_progress(
            page_number=serializer.validated_data['page_number'],
            position=serializer.validated_data.get('position', 0)
        )

        # Update total listened time
        if 'listened_time' in serializer.validated_data:
            progress.total_listened_time += serializer.validated_data['listened_time']
            progress.save()

        # Increment book listen count (only once per user)
        if created:
            book.increment_listen_count()

        return APIResponse.success(
            data={
                "current_page": progress.current_page,
                "current_position": progress.current_position,
                "completion_percentage": progress.completion_percentage,
                "total_listened_time": progress.total_listened_time,
                "is_completed": progress.is_completed
            },
            message="Progress updated successfully"
        )


class MyLibraryView(APIView):
    """
    API to manage user's library

    Headers:
    Authorization: Bearer <token>

    GET /api/library/
    - List all books in library

    Query Parameters:
    - favorites_only: true/false

    Response:
    {
        "data": [
            {
                "id": 1,
                "book": {...},
                "is_favorite": true,
                "added_at": "2025-01-01T00:00:00Z"
            }
        ],
        "status": "PASS",
        "http_code": 200,
        "message": "Library retrieved successfully"
    }
    """

    def get(self, request):
        # Authenticate user
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        # Get library
        queryset = UserLibrary.objects.filter(user=user)

        # Filter favorites if requested
        favorites_only = request.query_params.get('favorites_only', '').lower() == 'true'
        if favorites_only:
            queryset = queryset.filter(is_favorite=True)

        # Order by latest
        queryset = queryset.order_by('-added_at')

        # Serialize
        serializer = UserLibrarySerializer(queryset, many=True)

        return APIResponse.success(
            data=serializer.data,
            message="Library retrieved successfully"
        )


class LibraryAddView(APIView):
    """
    API to add book to library

    Headers:
    Authorization: Bearer <token>

    POST /api/library/add/
    Payload:
    {
        "book_id": 1
    }

    Response:
    {
        "data": {
            "message": "Book added to library"
        },
        "status": "PASS",
        "http_code": 201,
        "message": "Book added to library successfully"
    }
    """

    def post(self, request):
        # Authenticate user
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        # Get book_id
        book_id = request.data.get('book_id')
        if not book_id:
            return APIResponse.validation_error(
                message="book_id is required",
                errors={"book_id": ["This field is required"]}
            )

        # Get book
        book = get_object_or_404(Book, id=book_id, is_active=True)

        # Check if already in library
        if UserLibrary.objects.filter(user=user, book=book).exists():
            return APIResponse.error(
                message="Book already in library",
                http_code=400
            )

        # Add to library
        UserLibrary.objects.create(user=user, book=book)

        return APIResponse.success(
            data={"message": "Book added to library"},
            message="Book added to library successfully",
            http_code=201
        )


class LibraryRemoveView(APIView):
    """
    API to remove book from library

    Headers:
    Authorization: Bearer <token>

    DELETE /api/library/<book_id>/

    Response:
    {
        "data": {
            "message": "Book removed from library"
        },
        "status": "PASS",
        "http_code": 200,
        "message": "Book removed from library successfully"
    }
    """

    def delete(self, request, book_id):
        # Authenticate user
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        # Get library item
        library_item = get_object_or_404(
            UserLibrary,
            user=user,
            book_id=book_id
        )

        # Delete
        library_item.delete()

        return APIResponse.success(
            data={"message": "Book removed from library"},
            message="Book removed from library successfully"
        )


class ToggleFavoriteView(APIView):
    """
    API to toggle favorite status of a book

    Headers:
    Authorization: Bearer <token>

    POST /api/library/<book_id>/favorite/

    Response:
    {
        "data": {
            "is_favorite": true,
            "message": "Book marked as favorite"
        },
        "status": "PASS",
        "http_code": 200,
        "message": "Favorite status updated"
    }
    """

    def post(self, request, book_id):
        # Authenticate user
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        # Get book
        book = get_object_or_404(Book, id=book_id, is_active=True)

        # Get or create library item
        library_item, created = UserLibrary.objects.get_or_create(
            user=user,
            book=book
        )

        # Toggle favorite
        library_item.toggle_favorite()

        message = "Book marked as favorite" if library_item.is_favorite else "Book removed from favorites"

        return APIResponse.success(
            data={
                "is_favorite": library_item.is_favorite,
                "message": message
            },
            message="Favorite status updated successfully"
        )


class MyProgressView(APIView):
    """
    API to get user's listening progress for all books

    Headers:
    Authorization: Bearer <token>

    Query Parameters:
    - in_progress: true/false - Show only books in progress
    - completed: true/false - Show only completed books

    Response:
    {
        "data": [
            {
                "book": {...},
                "current_page": 10,
                "completion_percentage": 6,
                "last_listened_at": "2025-01-01T00:00:00Z"
            }
        ],
        "status": "PASS",
        "http_code": 200,
        "message": "Progress retrieved successfully"
    }
    """

    def get(self, request):
        # Authenticate user
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        # Get progress
        queryset = ListeningProgress.objects.filter(user=user)

        # Apply filters
        in_progress = request.query_params.get('in_progress', '').lower() == 'true'
        completed = request.query_params.get('completed', '').lower() == 'true'

        if in_progress:
            queryset = queryset.filter(is_completed=False, completion_percentage__gt=0)
        elif completed:
            queryset = queryset.filter(is_completed=True)

        # Order by last listened
        queryset = queryset.order_by('-last_listened_at')

        # Serialize
        serializer = ListeningProgressSerializer(queryset, many=True)

        return APIResponse.success(
            data=serializer.data,
            message="Progress retrieved successfully"
        )
