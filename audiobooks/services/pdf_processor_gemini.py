"""
PDF Processing Service with Google Gemini Vision API
Faster and more accurate Hindi text extraction compared to Tesseract OCR
Optimized for Render free tier performance
"""
import google.generativeai as genai
from pdf2image import convert_from_path
import pdfplumber
import logging
import os
import base64
import time
from io import BytesIO
from PIL import Image
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)


class PDFProcessorGemini:
    """
    Service class for processing PDF files with Google Gemini Vision API
    Significantly faster than Tesseract OCR, ideal for Render free tier
    """

    @staticmethod
    def extract_pages_with_gemini(pdf_file_path, language='hindi', progress_callback=None):
        """
        Extract text from all pages of a PDF file using Gemini Vision API

        Args:
            pdf_file_path: Path to PDF file
            language: Language of the document (default: 'hindi')
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
            # Configure Gemini API
            api_key = os.environ.get('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables")

            genai.configure(api_key=api_key)

            # Use Gemini 2.5 Flash - stable and fast for free tier
            # Best balance of speed and quality
            model = genai.GenerativeModel('models/gemini-2.5-flash')

            print(f"\n[GEMINI SERVICE] Starting PDF processing...")
            print(f"[GEMINI SERVICE] PDF path: {pdf_file_path}")
            print(f"[GEMINI SERVICE] Language: {language}")

            pages_data = []

            # Get total page count
            print(f"[GEMINI SERVICE] Opening PDF to get page count...")
            with pdfplumber.open(pdf_file_path) as pdf:
                total_pages = len(pdf.pages)

            print(f"[GEMINI SERVICE] Total pages: {total_pages}")
            logger.info(f"Processing {total_pages} pages with Gemini Vision API (lang={language})")

            # Convert PDF pages to images
            print(f"[GEMINI SERVICE] Converting PDF to images...")
            logger.info("Converting PDF to images...")

            # Use lower DPI for faster processing and smaller image sizes
            # Gemini works well even with 150 DPI for text extraction
            images = convert_from_path(
                pdf_file_path,
                dpi=150,  # Balanced quality and speed
                fmt='jpeg'
            )

            print(f"[GEMINI SERVICE] Conversion complete. Got {len(images)} images")
            logger.info(f"Processing {len(images)} images with Gemini Vision API")

            # Create optimized prompt for Hindi text extraction
            extraction_prompt = PDFProcessorGemini._get_extraction_prompt(language)

            # Process each image with Gemini
            print(f"[GEMINI SERVICE] Starting Gemini processing loop...")
            for page_num, image in enumerate(images, start=1):
                print(f"[GEMINI SERVICE] Processing page {page_num}/{total_pages}...")

                # Add delay between requests to avoid rate limiting
                # Free tier: 15 RPM = 1 request per 4 seconds to be safe
                if page_num > 1:
                    delay = 5  # 5 seconds between pages = ~12 pages/minute (safe)
                    print(f"[GEMINI SERVICE] Waiting {delay}s to avoid rate limits...")
                    time.sleep(delay)

                try:
                    # Optimize image size to reduce tokens and improve speed
                    optimized_image = PDFProcessorGemini._optimize_image(image)

                    print(f"[GEMINI SERVICE] Calling Gemini API for page {page_num}...")

                    # Extract text using Gemini Vision with retry logic
                    text = PDFProcessorGemini._extract_with_retry(
                        model,
                        extraction_prompt,
                        optimized_image,
                        page_num
                    )

                    print(f"[GEMINI SERVICE] Gemini completed for page {page_num}. Extracted {len(text)} chars")

                    # Clean text
                    text = PDFProcessorGemini._clean_text(text)

                    pages_data.append({
                        'page_number': page_num,
                        'text': text
                    })

                    logger.info(f"Gemini extracted page {page_num}/{total_pages} ({len(text)} chars)")

                    # Call progress callback if provided
                    if progress_callback:
                        print(f"[GEMINI SERVICE] Calling progress callback for page {page_num}...")
                        progress_callback(page_num, total_pages, len(text))
                        print(f"[GEMINI SERVICE] Progress callback completed for page {page_num}")

                except Exception as e:
                    import traceback
                    print(f"[GEMINI SERVICE ERROR] Error on page {page_num}: {str(e)}")
                    print(f"[GEMINI SERVICE ERROR] Traceback: {traceback.format_exc()}")
                    logger.error(f"Gemini error on page {page_num}: {str(e)}")

                    # For quota errors, wait longer before failing
                    if "429" in str(e) or "quota" in str(e).lower():
                        print(f"[GEMINI SERVICE] Quota exceeded - waiting 60s before retry...")
                        time.sleep(60)

                        try:
                            text = PDFProcessorGemini._extract_with_retry(
                                model,
                                "Extract all text from this image.",
                                optimized_image,
                                page_num,
                                max_retries=1
                            )
                            pages_data.append({
                                'page_number': page_num,
                                'text': text
                            })
                            logger.info(f"Gemini quota retry successful for page {page_num}")
                        except:
                            pages_data.append({
                                'page_number': page_num,
                                'text': ""
                            })
                    else:
                        # Other errors - just save empty text
                        pages_data.append({
                            'page_number': page_num,
                            'text': ""
                        })

                    # Still call progress callback even on error
                    if progress_callback:
                        progress_callback(page_num, total_pages, 0)

            print(f"[GEMINI SERVICE] ✅ Processing complete!")
            print(f"[GEMINI SERVICE] Total pages processed: {total_pages}")
            print(f"[GEMINI SERVICE] Pages data count: {len(pages_data)}")
            print(f"[GEMINI SERVICE] Returning result...\n")

            return {
                'success': True,
                'total_pages': total_pages,
                'pages': pages_data,
                'error': None
            }

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"\n[GEMINI SERVICE ERROR] ❌ PDF extraction failed!")
            print(f"[GEMINI SERVICE ERROR] Error: {str(e)}")
            print(f"[GEMINI SERVICE ERROR] Traceback:\n{error_trace}\n")
            logger.error(f"PDF extraction failed: {str(e)}")
            return {
                'success': False,
                'total_pages': 0,
                'pages': [],
                'error': str(e)
            }

    @staticmethod
    def _extract_with_retry(model, prompt, image, page_num, max_retries=3):
        """
        Extract text with automatic retry on rate limit errors

        Args:
            model: Gemini model instance
            prompt: Extraction prompt
            image: PIL Image
            page_num: Current page number
            max_retries: Maximum retry attempts

        Returns:
            str: Extracted text
        """
        for attempt in range(max_retries):
            try:
                response = model.generate_content([prompt, image])
                return response.text if response else ""

            except google_exceptions.ResourceExhausted as e:
                # Rate limit or quota exceeded
                if attempt < max_retries - 1:
                    # Extract retry delay from error message if available
                    retry_delay = 15  # Default 15 seconds
                    error_str = str(e)
                    if "retry in" in error_str.lower():
                        try:
                            # Try to extract the delay from error message
                            import re
                            match = re.search(r'retry in ([\d.]+)s', error_str)
                            if match:
                                retry_delay = float(match.group(1)) + 2  # Add 2s buffer
                        except:
                            pass

                    print(f"[GEMINI RETRY] Rate limit hit on page {page_num}, waiting {retry_delay}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                else:
                    print(f"[GEMINI RETRY] Max retries reached for page {page_num}")
                    raise

            except Exception as e:
                # Other errors - fail immediately
                print(f"[GEMINI ERROR] Non-retryable error on page {page_num}: {str(e)}")
                raise

        return ""

    @staticmethod
    def _get_extraction_prompt(language):
        """
        Get optimized prompt for text extraction based on language

        Args:
            language: Target language (hindi, english, hinglish)

        Returns:
            str: Optimized prompt for Gemini
        """
        base_prompt = """Extract ALL text from this image exactly as it appears.
Maintain the original formatting, line breaks, and paragraph structure.
Include all characters, numbers, punctuation marks, and special symbols.
"""

        if language.lower() in ['hindi', 'hin']:
            return base_prompt + """
This is a Hindi language document. Please:
- Accurately recognize all Hindi Devanagari characters including matras (vowel marks)
- Preserve the correct spelling and diacritical marks
- Maintain proper word spacing and sentence structure
- Include any English words that appear in the text

Return only the extracted text without any additional commentary or formatting markers."""

        elif language.lower() in ['hinglish', 'hin+eng']:
            return base_prompt + """
This is a bilingual document with Hindi and English text. Please:
- Accurately recognize both Hindi Devanagari and English Latin characters
- Preserve all matras (vowel marks) and diacritical marks in Hindi text
- Maintain proper spacing between Hindi and English words
- Keep the original language of each word

Return only the extracted text without any additional commentary or formatting markers."""

        else:  # English or other
            return base_prompt + """
Return only the extracted text without any additional commentary, formatting markers, or explanations."""

    @staticmethod
    def _optimize_image(image):
        """
        Optimize image for Gemini API to reduce tokens and improve speed

        Args:
            image: PIL Image object

        Returns:
            PIL.Image: Optimized image
        """
        # Get current dimensions
        width, height = image.size

        # Gemini charges less for images ≤384 pixels (258 tokens)
        # For larger images, they're divided into 768x768 tiles
        # We'll resize to max 1536 pixels (2x2 tiles max) for good quality
        max_dimension = 1536

        if width > max_dimension or height > max_dimension:
            # Calculate new dimensions maintaining aspect ratio
            if width > height:
                new_width = max_dimension
                new_height = int((max_dimension / width) * height)
            else:
                new_height = max_dimension
                new_width = int((max_dimension / height) * width)

            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            print(f"[GEMINI SERVICE] Image resized from {width}x{height} to {new_width}x{new_height}")

        # Convert to RGB if needed (Gemini prefers RGB)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        return image

    @staticmethod
    def _clean_text(text):
        """
        Clean extracted text while preserving Hindi characters and formatting

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

        # Replace multiple spaces with single space while preserving line breaks
        text = '\n'.join(' '.join(line.split()) for line in text.split('\n'))

        return text.strip()

    @staticmethod
    def test_extraction(pdf_file_path, page_number=1):
        """
        Test Gemini extraction on a specific page

        Args:
            pdf_file_path: Path to PDF file
            page_number: Page to test (default: 1)

        Returns:
            str: Extracted text
        """
        try:
            logger.info(f"Testing Gemini extraction on page {page_number}")

            # Configure Gemini API
            api_key = os.environ.get('GEMINI_API_KEY')
            if not api_key:
                return "Error: GEMINI_API_KEY not found"

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')

            # Convert single page to image
            images = convert_from_path(
                pdf_file_path,
                first_page=page_number,
                last_page=page_number,
                dpi=150
            )

            if not images:
                return "No images found"

            # Extract text with Gemini
            prompt = PDFProcessorGemini._get_extraction_prompt('hindi')
            response = model.generate_content([prompt, images[0]])

            return response.text if response else "No text extracted"

        except Exception as e:
            logger.error(f"Gemini test failed: {str(e)}")
            return f"Error: {str(e)}"
