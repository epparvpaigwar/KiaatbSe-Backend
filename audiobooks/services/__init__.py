"""
Services package for audiobook processing
"""
from .pdf_processor import PDFProcessor
from .pdf_processor_ocr import PDFProcessorOCR
from .tts_generator import TTSGenerator

__all__ = ['PDFProcessor', 'PDFProcessorOCR', 'TTSGenerator']
