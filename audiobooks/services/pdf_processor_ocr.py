"""
PDF Processing Service with OCR
Uses Tesseract OCR for better Hindi text extraction
"""
import pytesseract
from pdf2image import convert_from_path
import pdfplumber
import logging
from PIL import Image
import tempfile
import os

logger = logging.getLogger(__name__)


class PDFProcessorOCR:
    """
    Service class for processing PDF files with OCR support
    Better for Hindi text extraction with proper matras and characters
    """

    @staticmethod
    def extract_pages_with_ocr(pdf_file_path, use_ocr=True, language='hin+eng', progress_callback=None):
        """
        Extract text from all pages of a PDF file using OCR

        Args:
            pdf_file_path: Path to PDF file
            use_ocr: Use OCR (True) or simple text extraction (False)
            language: Tesseract language code (default: 'hin+eng' for Hindi+English)
            progress_callback: Optional callback function(current_page, total_pages, chars_extracted)
                             Called after each page is processed for real-time progress updates

        Returns:
            dict: {
                'success': bool,
                'total_pages': int,
                'pages': [{'page_number': int, 'text': str}, ...],
                'error': str (if any)
            }
        """
        try:
            print(f"\n[OCR SERVICE] Starting PDF processing...")
            print(f"[OCR SERVICE] PDF path: {pdf_file_path}")
            print(f"[OCR SERVICE] Use OCR: {use_ocr}")
            print(f"[OCR SERVICE] Language: {language}")

            pages_data = []

            # First, get total page count
            print(f"[OCR SERVICE] Opening PDF to get page count...")
            with pdfplumber.open(pdf_file_path) as pdf:
                total_pages = len(pdf.pages)

            print(f"[OCR SERVICE] Total pages: {total_pages}")
            logger.info(f"Processing {total_pages} pages with OCR (lang={language})")

            if use_ocr:
                # Convert PDF pages to images for OCR
                print(f"[OCR SERVICE] Converting PDF to images...")
                logger.info("Converting PDF to images...")
                images = convert_from_path(
                    pdf_file_path,
                    dpi=150,  # Reduced DPI for faster processing (was 300)
                    fmt='jpeg'
                )

                print(f"[OCR SERVICE] Conversion complete. Got {len(images)} images")
                logger.info(f"Processing {len(images)} images with Tesseract OCR")

                # Process each image with OCR
                print(f"[OCR SERVICE] Starting OCR processing loop...")
                for page_num, image in enumerate(images, start=1):
                    print(f"[OCR SERVICE] Processing page {page_num}/{total_pages}...")
                    try:
                        # Extract text using Tesseract
                        print(f"[OCR SERVICE] Running Tesseract on page {page_num}...")
                        text = pytesseract.image_to_string(
                            image,
                            lang=language,
                            config='--psm 6'  # Assume uniform block of text
                        )
                        print(f"[OCR SERVICE] Tesseract completed for page {page_num}. Extracted {len(text)} chars")

                        # Clean text
                        text = PDFProcessorOCR._clean_text(text)

                        pages_data.append({
                            'page_number': page_num,
                            'text': text
                        })

                        logger.info(f"OCR extracted page {page_num}/{total_pages} ({len(text)} chars)")

                        # Call progress callback if provided
                        if progress_callback:
                            print(f"[OCR SERVICE] Calling progress callback for page {page_num}...")
                            progress_callback(page_num, total_pages, len(text))
                            print(f"[OCR SERVICE] Progress callback completed for page {page_num}")

                    except Exception as e:
                        import traceback
                        print(f"[OCR SERVICE ERROR] Error on page {page_num}: {str(e)}")
                        print(f"[OCR SERVICE ERROR] Traceback: {traceback.format_exc()}")
                        logger.error(f"OCR error on page {page_num}: {str(e)}")
                        pages_data.append({
                            'page_number': page_num,
                            'text': ""
                        })

                        # Still call progress callback even on error
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

                            # Call progress callback if provided
                            if progress_callback:
                                progress_callback(page_num, total_pages, len(text))

                        except Exception as e:
                            logger.error(f"Error extracting page {page_num}: {str(e)}")
                            pages_data.append({
                                'page_number': page_num,
                                'text': ""
                            })

            print(f"[OCR SERVICE] ✅ Processing complete!")
            print(f"[OCR SERVICE] Total pages processed: {total_pages}")
            print(f"[OCR SERVICE] Pages data count: {len(pages_data)}")
            print(f"[OCR SERVICE] Returning result...\n")

            return {
                'success': True,
                'total_pages': total_pages,
                'pages': pages_data,
                'error': None
            }

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"\n[OCR SERVICE ERROR] ❌ PDF extraction failed!")
            print(f"[OCR SERVICE ERROR] Error: {str(e)}")
            print(f"[OCR SERVICE ERROR] Traceback:\n{error_trace}\n")
            logger.error(f"PDF extraction failed: {str(e)}")
            return {
                'success': False,
                'total_pages': 0,
                'pages': [],
                'error': str(e)
            }

    @staticmethod
    def _clean_text(text):
        """
        Clean extracted text while preserving Hindi characters

        Args:
            text: Raw extracted text

        Returns:
            str: Cleaned text
        """
        if not text:
            return ""

        # Remove excessive whitespace but preserve paragraph breaks
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        text = '\n'.join(cleaned_lines)

        # Replace multiple spaces with single space
        text = ' '.join(text.split())

        return text.strip()

    @staticmethod
    def extract_page_image(pdf_file_path, page_number, output_path):
        """
        Extract a specific page as an image

        Args:
            pdf_file_path: Path to PDF file
            page_number: Page number to extract (1-indexed)
            output_path: Path to save image

        Returns:
            bool: Success status
        """
        try:
            images = convert_from_path(
                pdf_file_path,
                first_page=page_number,
                last_page=page_number,
                dpi=200
            )

            if images:
                images[0].save(output_path, 'JPEG', quality=85)
                logger.info(f"Page {page_number} saved as image: {output_path}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error extracting page image: {str(e)}")
            return False

    @staticmethod
    def test_ocr(pdf_file_path, page_number=1):
        """
        Test OCR on a specific page

        Args:
            pdf_file_path: Path to PDF file
            page_number: Page to test (default: 1)

        Returns:
            str: Extracted text
        """
        try:
            logger.info(f"Testing OCR on page {page_number}")

            # Convert single page to image
            images = convert_from_path(
                pdf_file_path,
                first_page=page_number,
                last_page=page_number,
                dpi=300
            )

            if not images:
                return "No images found"

            # Extract text with OCR
            text = pytesseract.image_to_string(
                images[0],
                lang='hin+eng',
                config='--psm 6'
            )

            return text

        except Exception as e:
            logger.error(f"OCR test failed: {str(e)}")
            return f"Error: {str(e)}"
