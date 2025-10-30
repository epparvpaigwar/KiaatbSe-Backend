"""
Serializers for Audiobook models
"""
from rest_framework import serializers
from .models import Book, BookPage, ListeningProgress, UserLibrary
from users.models import User


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info for nested serialization"""
    class Meta:
        model = User
        fields = ['id', 'name', 'email']


class BookPageSerializer(serializers.ModelSerializer):
    """Serializer for individual book pages"""
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = BookPage
        fields = [
            'id', 'page_number', 'text_content', 'audio_url',
            'audio_duration', 'processing_status', 'processing_error',
            'processed_at'
        ]

    def get_audio_url(self, obj):
        """Get audio file URL if available"""
        if obj.audio_file:
            return obj.audio_file.url if hasattr(obj.audio_file, 'url') else str(obj.audio_file)
        return None


class BookListSerializer(serializers.ModelSerializer):
    """Serializer for book list view"""
    uploader = UserBasicSerializer(read_only=True)
    cover_url = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'description', 'language', 'genre',
            'cover_url', 'total_pages', 'total_duration', 'uploader',
            'processing_status', 'processing_progress', 'is_public',
            'listen_count', 'favorite_count', 'uploaded_at',
            'progress_percentage'
        ]

    def get_cover_url(self, obj):
        """Get cover image URL"""
        if obj.cover_image:
            return obj.cover_image.url if hasattr(obj.cover_image, 'url') else str(obj.cover_image)
        return None

    def get_progress_percentage(self, obj):
        """Get user's progress for this book"""
        request = self.context.get('request')
        if request and request.user:
            try:
                progress = ListeningProgress.objects.get(
                    user=request.user,
                    book=obj
                )
                return progress.completion_percentage
            except ListeningProgress.DoesNotExist:
                return 0
        return None


class BookDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for book detail view"""
    uploader = UserBasicSerializer(read_only=True)
    cover_url = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    pages_count = serializers.SerializerMethodField()
    is_in_library = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()
    user_progress = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'author', 'description', 'language', 'genre',
            'cover_url', 'pdf_url', 'total_pages', 'total_duration',
            'uploader', 'processing_status', 'processing_progress',
            'processing_error', 'is_public', 'is_active',
            'listen_count', 'favorite_count', 'uploaded_at',
            'processed_at', 'pages_count', 'is_in_library',
            'is_favorite', 'user_progress'
        ]

    def get_cover_url(self, obj):
        if obj.cover_image:
            return obj.cover_image.url if hasattr(obj.cover_image, 'url') else str(obj.cover_image)
        return None

    def get_pdf_url(self, obj):
        """Get PDF URL (only for uploader)"""
        request = self.context.get('request')
        if request and request.user and obj.uploader == request.user:
            if obj.pdf_file:
                return obj.pdf_file.url if hasattr(obj.pdf_file, 'url') else str(obj.pdf_file)
        return None

    def get_pages_count(self, obj):
        return obj.pages.count()

    def get_is_in_library(self, obj):
        """Check if book is in user's library"""
        request = self.context.get('request')
        if request and request.user:
            return UserLibrary.objects.filter(
                user=request.user,
                book=obj
            ).exists()
        return False

    def get_is_favorite(self, obj):
        """Check if book is favorited by user"""
        request = self.context.get('request')
        if request and request.user:
            try:
                library_item = UserLibrary.objects.get(
                    user=request.user,
                    book=obj
                )
                return library_item.is_favorite
            except UserLibrary.DoesNotExist:
                return False
        return False

    def get_user_progress(self, obj):
        """Get detailed user progress"""
        request = self.context.get('request')
        if request and request.user:
            try:
                progress = ListeningProgress.objects.get(
                    user=request.user,
                    book=obj
                )
                return {
                    'current_page': progress.current_page,
                    'current_position': progress.current_position,
                    'completion_percentage': progress.completion_percentage,
                    'total_listened_time': progress.total_listened_time,
                    'is_completed': progress.is_completed,
                    'last_listened_at': progress.last_listened_at
                }
            except ListeningProgress.DoesNotExist:
                return None
        return None


class BookUploadSerializer(serializers.ModelSerializer):
    """Serializer for book upload"""
    pdf_file = serializers.FileField(required=True)
    cover_image = serializers.ImageField(required=False)

    class Meta:
        model = Book
        fields = [
            'title', 'author', 'description', 'language', 'genre',
            'pdf_file', 'cover_image', 'is_public'
        ]

    def validate_pdf_file(self, value):
        """Validate PDF file"""
        # Check file size (max 50MB)
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("PDF file size cannot exceed 50MB")

        # Check file extension
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError("Only PDF files are allowed")

        return value

    def validate_cover_image(self, value):
        """Validate cover image"""
        if value:
            # Check file size (max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Image size cannot exceed 5MB")

            # Check file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError("Only JPEG and PNG images are allowed")

        return value


class ListeningProgressSerializer(serializers.ModelSerializer):
    """Serializer for listening progress"""
    book = BookListSerializer(read_only=True)

    class Meta:
        model = ListeningProgress
        fields = [
            'id', 'book', 'current_page', 'current_position',
            'total_listened_time', 'is_completed',
            'completion_percentage', 'started_at',
            'last_listened_at', 'completed_at'
        ]


class UserLibrarySerializer(serializers.ModelSerializer):
    """Serializer for user library"""
    book = BookListSerializer(read_only=True)

    class Meta:
        model = UserLibrary
        fields = [
            'id', 'book', 'is_favorite', 'notes',
            'added_at', 'favorited_at'
        ]


class ProgressUpdateSerializer(serializers.Serializer):
    """Serializer for updating listening progress"""
    page_number = serializers.IntegerField(min_value=1, required=True)
    position = serializers.IntegerField(min_value=0, default=0)
    listened_time = serializers.IntegerField(min_value=0, default=0)
