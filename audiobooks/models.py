"""
Audiobook models for KitaabSe platform
Handles books, pages, progress tracking, and user libraries
"""
from django.db import models
from django.utils import timezone
from users.models import User
from cloudinary.models import CloudinaryField


class Book(models.Model):
    """
    Main Book model - represents an uploaded book/audiobook
    """
    LANGUAGE_CHOICES = [
        ('hindi', 'Hindi'),
        ('english', 'English'),
        ('urdu', 'Urdu'),
        ('bengali', 'Bengali'),
        ('tamil', 'Tamil'),
        ('telugu', 'Telugu'),
        ('marathi', 'Marathi'),
        ('gujarati', 'Gujarati'),
        ('other', 'Other'),
    ]

    GENRE_CHOICES = [
        ('literature', 'Literature'),
        ('fiction', 'Fiction'),
        ('non_fiction', 'Non-Fiction'),
        ('poetry', 'Poetry'),
        ('drama', 'Drama'),
        ('biography', 'Biography'),
        ('history', 'History'),
        ('science', 'Science'),
        ('philosophy', 'Philosophy'),
        ('religion', 'Religion'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    # Basic Information
    title = models.CharField(max_length=300)
    author = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='hindi')
    genre = models.CharField(max_length=50, choices=GENRE_CHOICES, blank=True, null=True)

    # File Storage
    pdf_file = CloudinaryField('pdfs', resource_type='raw', folder='kitaabse/pdfs')
    cover_image = CloudinaryField('covers', blank=True, null=True, folder='kitaabse/covers')

    # Metadata
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_books')
    total_pages = models.IntegerField(default=0)
    total_duration = models.IntegerField(default=0, help_text='Total audio duration in seconds')

    # Processing Status
    processing_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    processing_progress = models.IntegerField(default=0, help_text='Percentage of pages processed')
    processing_error = models.TextField(blank=True, null=True)

    # Visibility
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    # Stats
    listen_count = models.IntegerField(default=0)
    favorite_count = models.IntegerField(default=0)

    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'books'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['uploader', 'is_public']),
            models.Index(fields=['language', 'is_public']),
            models.Index(fields=['genre', 'is_public']),
            models.Index(fields=['processing_status']),
            models.Index(fields=['-uploaded_at']),
        ]

    def __str__(self):
        return f"{self.title} by {self.author or 'Unknown'}"

    def increment_listen_count(self):
        """Increment listen count"""
        self.listen_count += 1
        self.save(update_fields=['listen_count'])

    def increment_favorite_count(self):
        """Increment favorite count"""
        self.favorite_count += 1
        self.save(update_fields=['favorite_count'])

    def decrement_favorite_count(self):
        """Decrement favorite count"""
        if self.favorite_count > 0:
            self.favorite_count -= 1
            self.save(update_fields=['favorite_count'])


class BookPage(models.Model):
    """
    Individual page of a book with extracted text and generated audio
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    # Relationships
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='pages')

    # Page Information
    page_number = models.IntegerField()
    text_content = models.TextField(blank=True, help_text='Extracted text from PDF page')

    # Audio Information
    audio_file = CloudinaryField('audio', blank=True, null=True, resource_type='video', folder='kitaabse/audio')
    audio_duration = models.IntegerField(default=0, help_text='Audio duration in seconds')

    # Processing Status
    processing_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processing_error = models.TextField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'book_pages'
        ordering = ['book', 'page_number']
        unique_together = ['book', 'page_number']
        indexes = [
            models.Index(fields=['book', 'page_number']),
            models.Index(fields=['processing_status']),
        ]

    def __str__(self):
        return f"{self.book.title} - Page {self.page_number}"


class ListeningProgress(models.Model):
    """
    Track user's listening progress for each book
    """
    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='listening_progress')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='progress_records')

    # Progress Information
    current_page = models.IntegerField(default=1, help_text='Last page listened to')
    current_position = models.IntegerField(default=0, help_text='Position in current page audio (seconds)')
    total_listened_time = models.IntegerField(default=0, help_text='Total time listened in seconds')

    # Status
    is_completed = models.BooleanField(default=False)
    completion_percentage = models.IntegerField(default=0, help_text='Percentage of book completed')

    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    last_listened_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'listening_progress'
        unique_together = ['user', 'book']
        ordering = ['-last_listened_at']
        indexes = [
            models.Index(fields=['user', '-last_listened_at']),
            models.Index(fields=['user', 'is_completed']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.book.title} ({self.completion_percentage}%)"

    def update_progress(self, page_number, position=0):
        """Update listening progress"""
        self.current_page = page_number
        self.current_position = position
        self.last_listened_at = timezone.now()

        # Calculate completion percentage
        if self.book.total_pages > 0:
            self.completion_percentage = int((page_number / self.book.total_pages) * 100)

            # Check if completed
            if self.completion_percentage >= 95:  # Consider 95% as completed
                self.is_completed = True
                if not self.completed_at:
                    self.completed_at = timezone.now()

        self.save()


class UserLibrary(models.Model):
    """
    User's personal library - saved books and favorites
    """
    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='library')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='in_libraries')

    # Library Information
    is_favorite = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True, help_text='User notes about the book')

    # Timestamps
    added_at = models.DateTimeField(auto_now_add=True)
    favorited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_library'
        unique_together = ['user', 'book']
        ordering = ['-added_at']
        indexes = [
            models.Index(fields=['user', 'is_favorite']),
            models.Index(fields=['user', '-added_at']),
        ]

    def __str__(self):
        return f"{self.user.email}'s library - {self.book.title}"

    def toggle_favorite(self):
        """Toggle favorite status"""
        if self.is_favorite:
            self.is_favorite = False
            self.favorited_at = None
            self.book.decrement_favorite_count()
        else:
            self.is_favorite = True
            self.favorited_at = timezone.now()
            self.book.increment_favorite_count()
        self.save()
