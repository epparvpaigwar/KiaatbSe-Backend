"""
PDF Processing Service
Extracts text from PDF files page by page
"""
import PyPDF2
import pdfplumber
import logging
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Service class for processing PDF files
    """

    @staticmethod
    def extract_pages(pdf_file_path):
        """
        Extract text from all pages of a PDF file

        Args:
            pdf_file_path: Path or file-like object of PDF

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

            # Try with pdfplumber first (better text extraction)
            with pdfplumber.open(pdf_file_path) as pdf:
                total_pages = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages, start=1):
                    try:
                        # Extract text from page
                        text = page.extract_text() or ""

                        # Clean text
                        text = PDFProcessor._clean_text(text)

                        pages_data.append({
                            'page_number': page_num,
                            'text': text
                        })

                        logger.info(f"Extracted page {page_num}/{total_pages}")

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

    @staticmethod
    def _clean_text(text):
        """
        Clean extracted text

        Args:
            text: Raw extracted text

        Returns:
            str: Cleaned text
        """
        if not text:
            return ""

        # Remove extra whitespace
        text = ' '.join(text.split())

        # Remove special characters that might cause issues
        # But keep Hindi/Devanagari characters
        text = text.strip()

        return text

    @staticmethod
    def get_page_count(pdf_file_path):
        """
        Get total number of pages in PDF

        Args:
            pdf_file_path: Path or file-like object of PDF

        Returns:
            int: Number of pages
        """
        try:
            with pdfplumber.open(pdf_file_path) as pdf:
                return len(pdf.pages)
        except Exception as e:
            logger.error(f"Error getting page count: {str(e)}")
            return 0

    @staticmethod
    def generate_cover_image(pdf_file_path, output_path):
        """
        Generate cover image from first page of PDF

        Args:
            pdf_file_path: Path to PDF file
            output_path: Path to save cover image

        Returns:
            bool: Success status
        """
        try:
            with pdfplumber.open(pdf_file_path) as pdf:
                first_page = pdf.pages[0]

                # Convert first page to image
                img = first_page.to_image(resolution=150)
                pil_img = img.original

                # Resize to thumbnail size
                pil_img.thumbnail((400, 600), Image.Resampling.LANCZOS)

                # Save as JPEG
                pil_img.save(output_path, 'JPEG', quality=85)

                logger.info(f"Cover image generated: {output_path}")
                return True

        except Exception as e:
            logger.error(f"Cover generation failed: {str(e)}")
            return False

    @staticmethod
    def validate_pdf(pdf_file_path):
        """
        Validate if file is a valid PDF

        Args:
            pdf_file_path: Path or file-like object

        Returns:
            dict: {'valid': bool, 'error': str}
        """
        try:
            with PyPDF2.PdfReader(pdf_file_path) as reader:
                # Check if PDF has pages
                if len(reader.pages) == 0:
                    return {'valid': False, 'error': 'PDF has no pages'}

                # Check if encrypted
                if reader.is_encrypted:
                    return {'valid': False, 'error': 'PDF is encrypted'}

                return {'valid': True, 'error': None}

        except Exception as e:
            return {'valid': False, 'error': f'Invalid PDF: {str(e)}'}
