"""
Synchronous Audio Generator
Generates audio for book pages during upload request (no Celery required)
"""

import tempfile
import os
import logging
from django.utils import timezone
import cloudinary.uploader

from .models import BookPage
from .services import TTSGenerator

logger = logging.getLogger(__name__)


def generate_audio_for_page(book, page, language='hindi'):
    """
    Generate audio for a single page synchronously.

    Args:
        book: Book model instance
        page: BookPage model instance
        language: Language for TTS (hindi, english, etc.)

    Returns:
        dict: Result with success status, duration, and audio_url
    """
    try:
        # Skip if already completed
        if page.processing_status == 'completed' and page.audio_file:
            return {
                'success': True,
                'message': 'Already processed',
                'duration': page.audio_duration or 0,
                'audio_url': page.audio_file
            }

        # Update status to processing
        page.processing_status = 'processing'
        page.save()

        # Check if page has text content
        if not page.text_content or page.text_content.strip() == "":
            page.processing_status = 'completed'
            page.processing_error = 'No text content'
            page.save()
            return {
                'success': True,
                'message': 'No text content (skipped)',
                'duration': 0,
                'audio_url': None
            }

        # Generate audio using Edge TTS
        temp_audio = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)

        try:
            result = TTSGenerator.generate_audio(
                text=page.text_content,
                output_path=temp_audio.name,
                language=language,
                gender='female'
            )

            if not result['success']:
                raise Exception(result.get('error', 'TTS generation failed'))

            # Upload audio to Cloudinary
            upload_result = cloudinary.uploader.upload(
                temp_audio.name,
                resource_type='video',  # MP3 is uploaded as video
                folder=f'kitaabse/audio/book_{book.id}',
                public_id=f'page_{page.page_number:04d}',
                overwrite=True
            )

            # Update page with audio info
            page.audio_file = upload_result['secure_url']
            page.audio_duration = result['duration']
            page.processing_status = 'completed'
            page.processed_at = timezone.now()
            page.save()

            return {
                'success': True,
                'message': 'Audio generated successfully',
                'duration': result['duration'],
                'audio_url': upload_result['secure_url']
            }

        finally:
            # Clean up temp file
            temp_audio.close()
            if os.path.exists(temp_audio.name):
                os.remove(temp_audio.name)

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Audio generation failed for page {page.page_number}: {error_msg}")

        # Update page status to failed
        page.processing_status = 'failed'
        page.processing_error = error_msg
        page.save()

        return {
            'success': False,
            'message': error_msg,
            'duration': 0,
            'audio_url': None
        }


def generate_all_audio_for_book(book, progress_callback=None):
    """
    Generate audio for all pages of a book synchronously.

    Args:
        book: Book model instance
        progress_callback: Optional callback function(page_num, total, result)

    Returns:
        dict: Summary with success count, failed count, total duration
    """
    pages = BookPage.objects.filter(book=book).order_by('page_number')
    total_pages = pages.count()

    success_count = 0
    failed_count = 0
    skipped_count = 0
    total_duration = 0

    for page in pages:
        result = generate_audio_for_page(book, page, language=book.language)

        if result['success']:
            if result['message'] == 'No text content (skipped)':
                skipped_count += 1
            else:
                success_count += 1
                total_duration += result.get('duration', 0)
        else:
            failed_count += 1

        # Call progress callback if provided
        if progress_callback:
            progress_callback(
                page.page_number,
                total_pages,
                result
            )

    # Update book status
    if failed_count == 0:
        book.processing_status = 'completed'
        book.processing_progress = 100
    else:
        book.processing_status = 'completed'  # Still mark as completed
        book.processing_progress = int((success_count + skipped_count) / total_pages * 100)

    book.total_duration = total_duration
    book.processed_at = timezone.now()
    book.save()

    return {
        'total_pages': total_pages,
        'success_count': success_count,
        'failed_count': failed_count,
        'skipped_count': skipped_count,
        'total_duration': total_duration
    }
