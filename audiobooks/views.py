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
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse
import json
import logging
import tempfile
import os

from users.utils import APIResponse, get_user_from_token
from .models import Book, BookPage, ListeningProgress, UserLibrary
from .serializers import (
    BookListSerializer, BookDetailSerializer, BookUploadSerializer,
    BookPageSerializer, ListeningProgressSerializer, UserLibrarySerializer,
    ProgressUpdateSerializer
)

logger = logging.getLogger(__name__)


def send_sse_event(event_type, data):
    """Helper function to format SSE events"""
    json_data = json.dumps(data)
    return f"event: {event_type}\ndata: {json_data}\n\n"


@method_decorator(csrf_exempt, name='dispatch')
class BookUploadView(APIView):
    """
    API to upload a book PDF with real-time SSE progress updates.

    Audio is generated SYNCHRONOUSLY during the upload request.
    No background workers needed!

    Headers:
    Authorization: Bearer <token>

    Payload (multipart/form-data):
    {
        "title": "Book Title",
        "author": "Author Name",
        "description": "Book description",
        "language": "hindi",  // hindi, english, hinglish
        "genre": "literature",
        "pdf_file": <PDF file>,
        "cover_image": <Image file> (optional),
        "is_public": true
    }

    SSE Events:
    - event: status - General status updates
    - event: processing_started - Text extraction started with total_pages
    - event: text_progress - Individual page text extraction progress
    - event: audio_started - Audio generation started
    - event: audio_progress - Individual page audio generation progress
    - event: completed - Upload and audio generation complete
    - event: error - Error occurred

    Example SSE Response:
    event: status
    data: {"message": "Starting upload process..."}

    event: processing_started
    data: {"total_pages": 10, "message": "Extracting text from 10 pages..."}

    event: text_progress
    data: {"current_page": 1, "total_pages": 10, "progress": 10, "chars": 1500}

    event: audio_started
    data: {"message": "Generating audio for 10 pages...", "total_pages": 10, "book_id": 123}

    event: audio_progress
    data: {"current_page": 1, "total_pages": 10, "progress": 10, "status": "completed", "duration": 45.5}

    event: completed
    data: {"book_id": 123, "title": "My Book", "total_pages": 10, "total_duration": 450.5}

    Notes:
    - Requires authentication
    - PDF max size: 50MB
    - Cover image max size: 5MB
    - Response is always SSE (text/event-stream)
    - Audio generation happens synchronously during upload
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        return self._post_with_sse(request)

    def _post_with_sse(self, request):
        """Handle upload with Server-Sent Events for real-time progress"""

        # Authenticate user first
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            def error_stream():
                yield send_sse_event('error', {
                    'error': 'Authentication failed',
                    'details': str(e)
                })
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        # Validate file
        pdf_file = request.FILES.get('pdf_file')
        if not pdf_file:
            def error_stream():
                yield send_sse_event('error', {'error': 'No file provided'})
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        if not pdf_file.name.endswith('.pdf'):
            def error_stream():
                yield send_sse_event('error', {'error': 'Only PDF files are allowed'})
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        if pdf_file.size > 50 * 1024 * 1024:
            def error_stream():
                yield send_sse_event('error', {'error': 'File too large. Maximum 50MB'})
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        # Get metadata
        title = request.POST.get('title', pdf_file.name)
        author = request.POST.get('author', 'Unknown')
        language = request.POST.get('language', 'hindi')
        genre = request.POST.get('genre', 'literature')
        description = request.POST.get('description', '')
        is_public = request.POST.get('is_public', 'true').lower() == 'true'
        cover_image = request.FILES.get('cover_image')

        # Save to temp file
        try:
            temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            for chunk in pdf_file.chunks():
                temp_pdf.write(chunk)
            temp_pdf.close()
            temp_pdf_path = temp_pdf.name
        except Exception as e:
            def error_stream():
                yield send_sse_event('error', {'error': f'File save failed: {str(e)}'})
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['X-Accel-Buffering'] = 'no'
            return response

        def event_stream():
            book = None
            try:
                yield send_sse_event('status', {'message': 'Starting upload process...'})

                # Get page count
                import pdfplumber
                with pdfplumber.open(temp_pdf_path) as pdf:
                    total_pages = len(pdf.pages)

                yield send_sse_event('processing_started', {
                    'total_pages': total_pages,
                    'message': f'Extracting text from {total_pages} pages...'
                })

                # Process with Gemini - page by page with immediate SSE
                from .services.pdf_processor_gemini import PDFProcessorGemini

                gemini_language = 'hindi' if language in ['hindi', 'hinglish'] else 'english'

                # Extract text from all pages
                result = PDFProcessorGemini.extract_pages_with_gemini(
                    temp_pdf_path,
                    language=gemini_language,
                    progress_callback=None  # We'll send events after each step
                )

                if not result['success']:
                    yield send_sse_event('error', {
                        'error': 'Text extraction failed',
                        'details': result.get('error', 'Unknown error')
                    })
                    return

                # Send text extraction complete events
                for i, page_data in enumerate(result['pages']):
                    yield send_sse_event('text_progress', {
                        'current_page': i + 1,
                        'total_pages': total_pages,
                        'progress': int(((i + 1) / total_pages) * 100),
                        'message': f'Text extracted from page {i + 1}/{total_pages}',
                        'chars': len(page_data.get('text', ''))
                    })

                yield send_sse_event('status', {'message': 'Creating book record...'})

                # Create book
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

                # Save files to Cloudinary
                book.pdf_file = pdf_file
                if cover_image:
                    book.cover_image = cover_image
                book.save()

                yield send_sse_event('status', {'message': 'Creating page records...'})

                # Create BookPage records
                for page_data in result['pages']:
                    BookPage.objects.create(
                        book=book,
                        page_number=page_data['page_number'],
                        text_content=page_data['text'],
                        processing_status='pending'
                    )

                # Start audio generation
                yield send_sse_event('audio_started', {
                    'message': f'Generating audio for {total_pages} pages...',
                    'total_pages': total_pages,
                    'book_id': book.id
                })

                # Generate audio for each page
                from .audio_generator import generate_audio_for_page

                pages = BookPage.objects.filter(book=book).order_by('page_number')
                total_duration = 0
                success_count = 0
                failed_count = 0

                for page in pages:
                    page_num = page.page_number

                    # Send "generating" event before starting
                    yield send_sse_event('audio_progress', {
                        'current_page': page_num,
                        'total_pages': total_pages,
                        'progress': int(((page_num - 1) / total_pages) * 100),
                        'status': 'generating',
                        'message': f'Generating audio for page {page_num}...'
                    })

                    # Generate audio
                    audio_result = generate_audio_for_page(book, page, language=book.language)

                    if audio_result['success']:
                        success_count += 1
                        duration = audio_result.get('duration', 0)
                        total_duration += duration
                        msg = audio_result.get('message', 'Audio generated')
                        if 'skipped' in msg.lower() or 'no text' in msg.lower():
                            status_text = 'skipped'
                        else:
                            status_text = 'completed'
                    else:
                        failed_count += 1
                        duration = 0
                        status_text = 'failed'
                        msg = audio_result.get('message', 'Failed')

                    # Send completion event for this page
                    yield send_sse_event('audio_progress', {
                        'current_page': page_num,
                        'total_pages': total_pages,
                        'progress': int((page_num / total_pages) * 100),
                        'status': status_text,
                        'message': f'Page {page_num}: {msg}',
                        'duration': duration
                    })

                # Update book status
                book.total_duration = total_duration
                book.processing_status = 'completed'
                book.processing_progress = 100
                book.processed_at = timezone.now()
                book.save()

                # Send final completion event
                yield send_sse_event('completed', {
                    'book_id': book.id,
                    'title': book.title,
                    'author': book.author,
                    'total_pages': book.total_pages,
                    'total_duration': total_duration,
                    'audio_generated': success_count,
                    'audio_failed': failed_count,
                    'message': f'Upload complete! {success_count} audio files generated. Total duration: {total_duration}s'
                })

            except Exception as e:
                import traceback
                logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")

                # Update book status if created
                if book:
                    book.processing_status = 'failed'
                    book.processing_error = str(e)
                    book.save()

                yield send_sse_event('error', {
                    'error': 'Upload failed',
                    'details': str(e)
                })

            finally:
                # Cleanup temp file
                try:
                    if os.path.exists(temp_pdf_path):
                        os.unlink(temp_pdf_path)
                except:
                    pass

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class BookListView(APIView):
    """
    API to list all public books with filters and search

    Query Parameters:
    - page: Page number (default: 1)
    - search: Search in title/author/description
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
        search_query = request.query_params.get('search', '')
        language = request.query_params.get('language', '')
        genre = request.query_params.get('genre', '')
        processing_status = request.query_params.get('status', '')

        queryset = Book.objects.filter(is_public=True, is_active=True)

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

        queryset = queryset.order_by('-uploaded_at')

        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = BookListSerializer(page, many=True, context={'request': request})
            result = paginator.get_paginated_response(serializer.data)
            return APIResponse.success(data=result.data, message="Books retrieved successfully")

        serializer = BookListSerializer(queryset, many=True, context={'request': request})
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
    - status: Filter by processing_status (completed, processing, failed, etc.)

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
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        queryset = Book.objects.filter(uploader=user, is_active=True)
        processing_status = request.query_params.get('status', '')
        if processing_status:
            queryset = queryset.filter(processing_status=processing_status)

        queryset = queryset.order_by('-uploaded_at')
        serializer = BookListSerializer(queryset, many=True, context={'request': request})

        return APIResponse.success(data=serializer.data, message="Your books retrieved successfully")


class BookDetailView(APIView):
    """
    API to get, update, or delete book details

    GET /api/audiobooks/<book_id>/
    - Get detailed book information
    - Public books accessible to all
    - Private books only accessible to uploader

    PATCH /api/audiobooks/<book_id>/
    - Update book info (only uploader can update)
    - Allowed fields: title, author, description, genre, is_public

    DELETE /api/audiobooks/<book_id>/
    - Soft delete book (only uploader can delete)

    Headers:
    Authorization: Bearer <token> (required for private books, PATCH, DELETE)

    Response:
    {
        "data": {
            "id": 1,
            "title": "Book Title",
            "author": "Author",
            "total_pages": 150,
            "total_duration": 3600,
            "processing_status": "completed",
            ...
        },
        "status": "PASS",
        "http_code": 200,
        "message": "Book details retrieved successfully"
    }
    """

    def get(self, request, book_id):
        book = get_object_or_404(Book, id=book_id, is_active=True)

        if not book.is_public:
            try:
                user = get_user_from_token(request)
                if book.uploader != user:
                    return APIResponse.access_denied(message="This book is private")
            except AuthenticationFailed:
                return APIResponse.access_denied(message="This book is private. Please login.")

        serializer = BookDetailSerializer(book, context={'request': request})
        return APIResponse.success(data=serializer.data, message="Book details retrieved successfully")

    def patch(self, request, book_id):
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        book = get_object_or_404(Book, id=book_id, is_active=True)
        if book.uploader != user:
            return APIResponse.access_denied(message="You can only update your own books")

        allowed_fields = ['title', 'author', 'description', 'genre', 'is_public']
        for field in allowed_fields:
            if field in request.data:
                setattr(book, field, request.data[field])
        book.save()

        serializer = BookDetailSerializer(book, context={'request': request})
        return APIResponse.success(data=serializer.data, message="Book updated successfully")

    def delete(self, request, book_id):
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        book = get_object_or_404(Book, id=book_id, is_active=True)
        if book.uploader != user:
            return APIResponse.access_denied(message="You can only delete your own books")

        book.is_active = False
        book.save()
        return APIResponse.success(data={"id": book.id}, message="Book deleted successfully")


class BookPagesView(APIView):
    """
    API to get all pages of a book with audio URLs

    GET /api/audiobooks/<book_id>/pages/

    Headers:
    Authorization: Bearer <token> (required for private books)

    Response:
    {
        "data": {
            "book": {
                "id": 1,
                "title": "Book Title",
                "total_pages": 10,
                "processing_status": "completed",
                "total_duration": 450
            },
            "pages": [
                {
                    "id": 1,
                    "page_number": 1,
                    "text_content": "Page text...",
                    "audio_file": "https://cloudinary.com/audio/page_001.mp3",
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
        book = get_object_or_404(Book, id=book_id, is_active=True)

        if not book.is_public:
            try:
                user = get_user_from_token(request)
                if book.uploader != user:
                    return APIResponse.access_denied(message="This book is private")
            except AuthenticationFailed:
                return APIResponse.access_denied(message="This book is private. Please login.")

        pages = BookPage.objects.filter(book=book).order_by('page_number')
        serializer = BookPageSerializer(pages, many=True)

        return APIResponse.success(
            data={
                "book": {
                    "id": book.id,
                    "title": book.title,
                    "total_pages": book.total_pages,
                    "processing_status": book.processing_status,
                    "total_duration": book.total_duration
                },
                "pages": serializer.data
            },
            message="Book pages retrieved successfully"
        )


class UpdateProgressView(APIView):
    """
    API to get or update user's listening progress for a book

    GET /api/audiobooks/<book_id>/progress/
    - Get current listening progress

    PUT /api/audiobooks/<book_id>/progress/
    - Update listening progress

    Headers:
    Authorization: Bearer <token>

    PUT Payload:
    {
        "page_number": 5,
        "position": 120.5,  // seconds into current page audio
        "listened_time": 60  // additional time listened (optional)
    }

    Response:
    {
        "data": {
            "current_page": 5,
            "current_position": 120.5,
            "completion_percentage": 50,
            "total_listened_time": 1800,
            "is_completed": false,
            "last_listened_at": "2024-01-15T10:30:00Z"
        },
        "status": "PASS",
        "http_code": 200,
        "message": "Progress updated successfully"
    }
    """

    def get(self, request, book_id):
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        book = get_object_or_404(Book, id=book_id, is_active=True)
        progress, created = ListeningProgress.objects.get_or_create(user=user, book=book)

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
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        serializer = ProgressUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(message="Invalid input data", errors=serializer.errors)

        book = get_object_or_404(Book, id=book_id, is_active=True)
        progress, created = ListeningProgress.objects.get_or_create(user=user, book=book)

        progress.update_progress(
            page_number=serializer.validated_data['page_number'],
            position=serializer.validated_data.get('position', 0)
        )

        if 'listened_time' in serializer.validated_data:
            progress.total_listened_time += serializer.validated_data['listened_time']
            progress.save()

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
    API to get user's library (saved books)

    GET /api/audiobooks/library/

    Headers:
    Authorization: Bearer <token>

    Query Parameters:
    - favorites_only: true/false - Filter only favorite books

    Response:
    {
        "data": [
            {
                "id": 1,
                "book": {
                    "id": 1,
                    "title": "Book Title",
                    ...
                },
                "is_favorite": true,
                "added_at": "2024-01-15T10:30:00Z"
            }
        ],
        "status": "PASS",
        "http_code": 200,
        "message": "Library retrieved successfully"
    }
    """

    def get(self, request):
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        queryset = UserLibrary.objects.filter(user=user)
        favorites_only = request.query_params.get('favorites_only', '').lower() == 'true'
        if favorites_only:
            queryset = queryset.filter(is_favorite=True)

        queryset = queryset.order_by('-added_at')
        serializer = UserLibrarySerializer(queryset, many=True)

        return APIResponse.success(data=serializer.data, message="Library retrieved successfully")


class LibraryAddView(APIView):
    """
    API to add a book to user's library

    POST /api/audiobooks/library/add/

    Headers:
    Authorization: Bearer <token>

    Payload:
    {
        "book_id": 123
    }

    Response:
    {
        "data": {"message": "Book added to library"},
        "status": "PASS",
        "http_code": 201,
        "message": "Book added to library successfully"
    }
    """

    def post(self, request):
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        book_id = request.data.get('book_id')
        if not book_id:
            return APIResponse.validation_error(
                message="book_id is required",
                errors={"book_id": ["This field is required"]}
            )

        book = get_object_or_404(Book, id=book_id, is_active=True)
        if UserLibrary.objects.filter(user=user, book=book).exists():
            return APIResponse.error(message="Book already in library", http_code=400)

        UserLibrary.objects.create(user=user, book=book)
        return APIResponse.success(
            data={"message": "Book added to library"},
            message="Book added to library successfully",
            http_code=201
        )


class LibraryRemoveView(APIView):
    """
    API to remove a book from user's library

    DELETE /api/audiobooks/library/<book_id>/

    Headers:
    Authorization: Bearer <token>

    Response:
    {
        "data": {"message": "Book removed from library"},
        "status": "PASS",
        "http_code": 200,
        "message": "Book removed from library successfully"
    }
    """

    def delete(self, request, book_id):
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        library_item = get_object_or_404(UserLibrary, user=user, book_id=book_id)
        library_item.delete()

        return APIResponse.success(
            data={"message": "Book removed from library"},
            message="Book removed from library successfully"
        )


class ToggleFavoriteView(APIView):
    """
    API to toggle favorite status of a book in user's library

    POST /api/audiobooks/library/<book_id>/favorite/

    Headers:
    Authorization: Bearer <token>

    Notes:
    - If book is not in library, it will be added first
    - Toggles between favorite/not favorite

    Response:
    {
        "data": {
            "is_favorite": true,
            "message": "Book marked as favorite"
        },
        "status": "PASS",
        "http_code": 200,
        "message": "Favorite status updated successfully"
    }
    """

    def post(self, request, book_id):
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        book = get_object_or_404(Book, id=book_id, is_active=True)
        library_item, created = UserLibrary.objects.get_or_create(user=user, book=book)
        library_item.toggle_favorite()

        message = "Book marked as favorite" if library_item.is_favorite else "Book removed from favorites"
        return APIResponse.success(
            data={"is_favorite": library_item.is_favorite, "message": message},
            message="Favorite status updated successfully"
        )


class MyProgressView(APIView):
    """
    API to get user's listening progress for all books

    GET /api/audiobooks/progress/

    Headers:
    Authorization: Bearer <token>

    Query Parameters:
    - in_progress: true - Filter books that are in progress (not completed, >0%)
    - completed: true - Filter only completed books

    Response:
    {
        "data": [
            {
                "id": 1,
                "book": {
                    "id": 1,
                    "title": "Book Title",
                    ...
                },
                "current_page": 5,
                "completion_percentage": 50,
                "total_listened_time": 1800,
                "is_completed": false,
                "last_listened_at": "2024-01-15T10:30:00Z"
            }
        ],
        "status": "PASS",
        "http_code": 200,
        "message": "Progress retrieved successfully"
    }
    """

    def get(self, request):
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        queryset = ListeningProgress.objects.filter(user=user)

        in_progress = request.query_params.get('in_progress', '').lower() == 'true'
        completed = request.query_params.get('completed', '').lower() == 'true'

        if in_progress:
            queryset = queryset.filter(is_completed=False, completion_percentage__gt=0)
        elif completed:
            queryset = queryset.filter(is_completed=True)

        queryset = queryset.order_by('-last_listened_at')
        serializer = ListeningProgressSerializer(queryset, many=True)

        return APIResponse.success(data=serializer.data, message="Progress retrieved successfully")
