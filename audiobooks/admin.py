"""
Django Admin Configuration for Audiobooks
"""
from django.contrib import admin
from .models import Book, BookPage, ListeningProgress, UserLibrary


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    """Admin interface for Book model"""
    list_display = [
        'id', 'title', 'author', 'uploader', 'language', 'genre',
        'processing_status', 'processing_progress', 'total_pages',
        'is_public', 'listen_count', 'favorite_count', 'uploaded_at'
    ]
    list_filter = [
        'processing_status', 'language', 'genre', 'is_public',
        'is_active', 'uploaded_at'
    ]
    search_fields = ['title', 'author', 'description', 'uploader__email']
    readonly_fields = [
        'id', 'total_pages', 'total_duration', 'processing_progress',
        'listen_count', 'favorite_count', 'uploaded_at',
        'processed_at', 'modified_at'
    ]
    list_per_page = 25
    date_hierarchy = 'uploaded_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'title', 'author', 'description', 'uploader')
        }),
        ('Classification', {
            'fields': ('language', 'genre')
        }),
        ('Files', {
            'fields': ('pdf_file', 'cover_image')
        }),
        ('Processing Status', {
            'fields': (
                'processing_status', 'processing_progress',
                'processing_error', 'total_pages', 'total_duration'
            )
        }),
        ('Settings', {
            'fields': ('is_public', 'is_active')
        }),
        ('Statistics', {
            'fields': ('listen_count', 'favorite_count')
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'processed_at', 'modified_at')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('uploader')


@admin.register(BookPage)
class BookPageAdmin(admin.ModelAdmin):
    """Admin interface for BookPage model"""
    list_display = [
        'id', 'book_title', 'page_number', 'processing_status',
        'audio_duration', 'processed_at'
    ]
    list_filter = ['processing_status', 'created_at']
    search_fields = ['book__title', 'text_content']
    readonly_fields = [
        'id', 'audio_duration', 'created_at', 'processed_at'
    ]
    list_per_page = 50

    fieldsets = (
        ('Page Information', {
            'fields': ('id', 'book', 'page_number')
        }),
        ('Content', {
            'fields': ('text_content',)
        }),
        ('Audio', {
            'fields': ('audio_file', 'audio_duration')
        }),
        ('Processing', {
            'fields': ('processing_status', 'processing_error')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'processed_at')
        }),
    )

    def book_title(self, obj):
        return obj.book.title
    book_title.short_description = 'Book'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('book')


@admin.register(ListeningProgress)
class ListeningProgressAdmin(admin.ModelAdmin):
    """Admin interface for ListeningProgress model"""
    list_display = [
        'id', 'user_email', 'book_title', 'current_page',
        'completion_percentage', 'is_completed', 'last_listened_at'
    ]
    list_filter = ['is_completed', 'last_listened_at']
    search_fields = ['user__email', 'book__title']
    readonly_fields = [
        'id', 'started_at', 'last_listened_at', 'completed_at'
    ]
    list_per_page = 50
    date_hierarchy = 'last_listened_at'

    fieldsets = (
        ('User & Book', {
            'fields': ('id', 'user', 'book')
        }),
        ('Progress', {
            'fields': (
                'current_page', 'current_position',
                'completion_percentage', 'total_listened_time',
                'is_completed'
            )
        }),
        ('Timestamps', {
            'fields': ('started_at', 'last_listened_at', 'completed_at')
        }),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'

    def book_title(self, obj):
        return obj.book.title
    book_title.short_description = 'Book'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'book')


@admin.register(UserLibrary)
class UserLibraryAdmin(admin.ModelAdmin):
    """Admin interface for UserLibrary model"""
    list_display = [
        'id', 'user_email', 'book_title', 'is_favorite',
        'added_at', 'favorited_at'
    ]
    list_filter = ['is_favorite', 'added_at']
    search_fields = ['user__email', 'book__title']
    readonly_fields = ['id', 'added_at', 'favorited_at']
    list_per_page = 50
    date_hierarchy = 'added_at'

    fieldsets = (
        ('User & Book', {
            'fields': ('id', 'user', 'book')
        }),
        ('Library Settings', {
            'fields': ('is_favorite', 'notes')
        }),
        ('Timestamps', {
            'fields': ('added_at', 'favorited_at')
        }),
    )

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User'

    def book_title(self, obj):
        return obj.book.title
    book_title.short_description = 'Book'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'book')
