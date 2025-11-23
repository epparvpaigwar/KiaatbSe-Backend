"""
Quick test script to verify Gemini API setup
"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def test_gemini_api():
    """Test if Gemini API key works"""
    print("🔍 Testing Gemini API Setup...")
    print("-" * 60)

    # Check if API key exists
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in .env file")
        return False

    print(f"✅ API Key found: {api_key[:20]}...")

    try:
        # Configure Gemini
        genai.configure(api_key=api_key)
        print("✅ Gemini API configured successfully")

        # Test with a simple text prompt
        print("\n📝 Testing text generation...")
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content("Say 'Hello from Gemini!' in Hindi")

        print("✅ Test successful!")
        print("\n📋 Gemini Response:")
        print(f"   {response.text}")

        print("\n" + "=" * 60)
        print("🎉 SUCCESS! Your Gemini API is working correctly!")
        print("=" * 60)
        print("\n💡 Your audiobook app is now ready to use Gemini for")
        print("   fast Hindi text extraction from PDFs!")
        print("\n📊 Free Tier Limits:")
        print("   - 15 requests per minute")
        print("   - 1,500 requests per day")
        print("   - Perfect for ~500 pages/day")

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("   1. Verify your API key is correct")
        print("   2. Check your internet connection")
        print("   3. Ensure Gemini API is enabled in your Google account")
        return False

if __name__ == "__main__":
    test_gemini_api()
