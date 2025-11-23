#!/usr/bin/env python3
"""
Test PDF extraction with Gemini
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from audiobooks.services.pdf_processor_gemini import PDFProcessorGemini

# Test with the provided PDF
pdf_path = '/Users/apple/Desktop/temp/KiaatbSe-Backend/घर जमाई.pdf'

print("🧪 Testing PDF extraction with Gemini...")
print(f"📄 PDF: {pdf_path}")
print("="*60)

# Test extraction on just the first page
result = PDFProcessorGemini.test_extraction(pdf_path, page_number=1)

print("\n" + "="*60)
print("📝 Extracted Text from Page 1:")
print("="*60)
print(result)
print("\n" + "="*60)

if result and len(result) > 10 and "Error" not in result:
    print("✅ SUCCESS! Gemini is extracting Hindi text correctly!")
else:
    print("❌ FAILED! Check the error above")
