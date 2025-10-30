"""
Celery tasks for audiobook processing
Handles PDF extraction and audio generation in the background
"""
import logging
import tempfile
import os
from celery import shared_task
from django.utils import timezone
from .models import Book, BookPage
from .services import PDFProcessor, TTSGenerator
import cloudinary.uploader

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_book_pdf(self, book_id):
    """
    Process uploaded PDF: extract pages and create BookPage records

    Args:
        book_id: ID of the Book to process

    Returns:
        dict: Processing result
    """
    try:
        logger.info(f"Starting PDF processing for book ID: {book_id}")

        # Get book instance
        book = Book.objects.get(id=book_id)
        book.processing_status = 'processing'
        book.save()

        # Download PDF from Cloudinary to temp file
        pdf_url = book.pdf_file.url
        temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)

        try:
            # Download PDF content
            import requests
            response = requests.get(pdf_url)
            temp_pdf.write(response.content)
            temp_pdf.flush()

            # Extract text from all pages
            result = PDFProcessor.extract_pages(temp_pdf.name)

            if not result['success']:
                raise Exception(result['error'])

            # Update book total pages
            book.total_pages = result['total_pages']
            book.save()

            # Create BookPage records
            pages_created = 0
            for page_data in result['pages']:
                BookPage.objects.create(
                    book=book,
                    page_number=page_data['page_number'],
                    text_content=page_data['text'],
                    processing_status='pending'
                )
                pages_created += 1

            logger.info(f"Created {pages_created} page records for book {book_id}")

            # Schedule audio generation for each page
            for page_num in range(1, result['total_pages'] + 1):
                generate_page_audio.delay(book_id, page_num)

            return {
                'success': True,
                'book_id': book_id,
                'pages_created': pages_created
            }

        finally:
            # Clean up temp file
            temp_pdf.close()
            if os.path.exists(temp_pdf.name):
                os.remove(temp_pdf.name)

    except Book.DoesNotExist:
        logger.error(f"Book {book_id} not found")
        return {'success': False, 'error': 'Book not found'}

    except Exception as e:
        logger.error(f"PDF processing failed for book {book_id}: {str(e)}")

        # Update book status to failed
        try:
            book = Book.objects.get(id=book_id)
            book.processing_status = 'failed'
            book.processing_error = str(e)
            book.save()
        except:
            pass

        # Retry task if retries available
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_page_audio(self, book_id, page_number):
    """
    Generate audio for a specific page

    Args:
        book_id: ID of the Book
        page_number: Page number to generate audio for

    Returns:
        dict: Generation result
    """
    try:
        logger.info(f"Generating audio for book {book_id}, page {page_number}")

        # Get book and page
        book = Book.objects.get(id=book_id)
        page = BookPage.objects.get(book=book, page_number=page_number)

        # Skip if already processed
        if page.processing_status == 'completed':
            logger.info(f"Page {page_number} already processed, skipping")
            return {'success': True, 'message': 'Already processed'}

        # Update status
        page.processing_status = 'processing'
        page.save()

        # Check if page has text
        if not page.text_content or page.text_content.strip() == "":
            logger.warning(f"Page {page_number} has no text content")
            page.processing_status = 'completed'
            page.processing_error = 'No text content'
            page.save()
            return {'success': True, 'message': 'No text content'}

        # Generate audio using Edge TTS
        temp_audio = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)

        try:
            result = TTSGenerator.generate_audio(
                text=page.text_content,
                output_path=temp_audio.name,
                language=book.language,
                gender='female'  # Can be made configurable later
            )

            if not result['success']:
                raise Exception(result['error'])

            # Upload audio to Cloudinary
            upload_result = cloudinary.uploader.upload(
                temp_audio.name,
                resource_type='video',  # MP3 is uploaded as video
                folder=f'kitaabse/audio/book_{book_id}',
                public_id=f'page_{page_number:04d}',
                overwrite=True
            )

            # Update page with audio info
            page.audio_file = upload_result['secure_url']
            page.audio_duration = result['duration']
            page.processing_status = 'completed'
            page.processed_at = timezone.now()
            page.save()

            # Update book processing progress
            update_book_progress(book_id)

            logger.info(f"Audio generated successfully for page {page_number}")

            return {
                'success': True,
                'book_id': book_id,
                'page_number': page_number,
                'duration': result['duration']
            }

        finally:
            # Clean up temp file
            temp_audio.close()
            if os.path.exists(temp_audio.name):
                os.remove(temp_audio.name)

    except (Book.DoesNotExist, BookPage.DoesNotExist) as e:
        logger.error(f"Book or Page not found: {str(e)}")
        return {'success': False, 'error': str(e)}

    except Exception as e:
        logger.error(f"Audio generation failed: {str(e)}")

        # Update page status
        try:
            page = BookPage.objects.get(book_id=book_id, page_number=page_number)
            page.processing_status = 'failed'
            page.processing_error = str(e)
            page.save()
        except:
            pass

        # Retry task
        raise self.retry(exc=e, countdown=60)


def update_book_progress(book_id):
    """
    Update book processing progress percentage

    Args:
        book_id: ID of the Book
    """
    try:
        book = Book.objects.get(id=book_id)

        # Count completed pages
        total_pages = book.pages.count()
        completed_pages = book.pages.filter(processing_status='completed').count()

        if total_pages > 0:
            progress = int((completed_pages / total_pages) * 100)
            book.processing_progress = progress

            # If all pages completed, mark book as completed
            if completed_pages == total_pages:
                book.processing_status = 'completed'
                book.processed_at = timezone.now()

                # Calculate total duration
                total_duration = sum(
                    page.audio_duration for page in book.pages.all()
                )
                book.total_duration = total_duration

            book.save()
            logger.info(f"Book {book_id} progress updated: {progress}%")

    except Exception as e:
        logger.error(f"Error updating book progress: {str(e)}")


@shared_task
def cleanup_failed_books():
    """
    Cleanup task to retry or remove failed book processing
    Run periodically via Celery Beat
    """
    from datetime import timedelta

    # Find books stuck in processing for > 2 hours
    two_hours_ago = timezone.now() - timedelta(hours=2)
    stuck_books = Book.objects.filter(
        processing_status='processing',
        modified_at__lt=two_hours_ago
    )

    for book in stuck_books:
        logger.warning(f"Book {book.id} stuck in processing, marking as failed")
        book.processing_status = 'failed'
        book.processing_error = 'Processing timeout'
        book.save()


@shared_task
def retry_failed_pages():
    """
    Retry audio generation for failed pages
    Run periodically via Celery Beat
    """
    # Find pages that failed less than 24 hours ago
    from datetime import timedelta
    yesterday = timezone.now() - timedelta(hours=24)

    failed_pages = BookPage.objects.filter(
        processing_status='failed',
        created_at__gte=yesterday
    )

    for page in failed_pages:
        logger.info(f"Retrying audio generation for page {page.id}")
        generate_page_audio.delay(page.book.id, page.page_number)
