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

from users.utils import APIResponse, get_user_from_token
from .models import Book, BookPage, ListeningProgress, UserLibrary
from .serializers import (
    BookListSerializer, BookDetailSerializer, BookUploadSerializer,
    BookPageSerializer, ListeningProgressSerializer, UserLibrarySerializer,
    ProgressUpdateSerializer
)
from .tasks import process_book_pdf


@method_decorator(csrf_exempt, name='dispatch')
class BookUploadView(APIView):
    """
    API to upload a book PDF and start processing

    Headers:
    Authorization: Bearer <token>

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

    Response (201):
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

    Notes:
    - Requires authentication
    - PDF max size: 50MB
    - Cover image max size: 5MB
    - Processing starts automatically in background
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # Authenticate user
        try:
            user = get_user_from_token(request)
        except AuthenticationFailed as e:
            return APIResponse.unauthorized(message=str(e))

        # Validate request data
        serializer = BookUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.validation_error(
                message="Invalid input data",
                errors=serializer.errors
            )

        # Process PDF immediately before saving
        import tempfile
        import os
        from .services import PDFProcessor

        pdf_file = request.FILES.get('pdf_file')
        if not pdf_file:
            return APIResponse.validation_error(message="PDF file is required")

        # Save PDF to temp file for processing
        temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        try:
            # Write uploaded PDF to temp file
            for chunk in pdf_file.chunks():
                temp_pdf.write(chunk)
            temp_pdf.close()

            # Extract text from PDF using OCR for better Hindi text extraction
            from .services import PDFProcessorOCR
            result = PDFProcessorOCR.extract_pages_with_ocr(
                temp_pdf.name,
                use_ocr=True,
                language='hin+eng'  # Hindi + English
            )

            if not result['success']:
                return APIResponse.error(
                    message=f"Failed to process PDF: {result['error']}",
                    http_code=400
                )

            # Create book record (this saves PDF to Cloudinary)
            book = serializer.save(uploader=user)
            book.total_pages = result['total_pages']
            book.processing_status = 'processing'
            book.save()

            # Create BookPage records
            for page_data in result['pages']:
                BookPage.objects.create(
                    book=book,
                    page_number=page_data['page_number'],
                    text_content=page_data['text'],
                    processing_status='pending'
                )

            # Trigger audio generation for each page
            from .tasks import generate_page_audio
            for page_num in range(1, result['total_pages'] + 1):
                generate_page_audio.delay(book.id, page_num)

            return APIResponse.success(
                data={
                    "id": book.id,
                    "title": book.title,
                    "total_pages": book.total_pages,
                    "processing_status": book.processing_status,
                    "message": "Book uploaded and text extracted. Audio generation started."
                },
                message=f"Book uploaded successfully. Processing {result['total_pages']} pages...",
                http_code=201
            )

        finally:
            # Clean up temp file
            try:
                os.remove(temp_pdf.name)
            except:
                pass


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
