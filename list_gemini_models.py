#!/usr/bin/env python3
"""
List all available Gemini models for your API key
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY not found in .env file")
    exit(1)

print(f"✅ API Key found: {api_key[:20]}...")
print("\n" + "="*60)
print("Available Gemini Models:")
print("="*60)

genai.configure(api_key=api_key)

# List all available models
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"\n📦 Model: {model.name}")
        print(f"   Display Name: {model.display_name}")
        print(f"   Supported: {', '.join(model.supported_generation_methods)}")
        print(f"   Input Token Limit: {model.input_token_limit}")
        print(f"   Output Token Limit: {model.output_token_limit}")

print("\n" + "="*60)
print("✅ Done!")
print("="*60)
