"""
Services package for audiobook processing
"""
from .pdf_processor import PDFProcessor
from .tts_generator import TTSGenerator

__all__ = ['PDFProcessor', 'TTSGenerator']
