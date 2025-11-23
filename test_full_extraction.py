#!/usr/bin/env python3
"""
Test full PDF extraction with rate limiting
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from audiobooks.services.pdf_processor_gemini import PDFProcessorGemini

# Test with the provided PDF (first 3 pages)
pdf_path = '/Users/apple/Desktop/temp/KiaatbSe-Backend/घर जमाई.pdf'

print("🧪 Testing Full PDF Extraction with Rate Limiting...")
print(f"📄 PDF: {pdf_path}")
print("="*60)

def progress_callback(current, total, chars):
    print(f"✅ Page {current}/{total} - {chars} characters extracted")

# Extract first 3 pages
result = PDFProcessorGemini.extract_pages_with_gemini(
    pdf_path,
    language='hindi',
    progress_callback=progress_callback
)

print("\n" + "="*60)
print("📊 Results:")
print("="*60)
print(f"Success: {result['success']}")
print(f"Total Pages: {result['total_pages']}")
print(f"Pages Processed: {len(result['pages'])}")

if result['success']:
    print("\n✅ FULL TEST SUCCESSFUL!")
    print("\n📝 Sample from first page:")
    print("-"*60)
    if result['pages']:
        sample = result['pages'][0]['text'][:200]
        print(sample + "...")
else:
    print(f"\n❌ Error: {result['error']}")
