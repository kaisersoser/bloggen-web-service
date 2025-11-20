#!/usr/bin/env python3
"""
Test script to validate Google Gemini API key and model access.
"""
import os
import sys
from pathlib import Path

# Add backend src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_google_api_key():
    """Test Google Gemini API key with a simple completion request."""
    
    # Set the API key
    api_key = "AIzaSyARNLa2esu6K9VhOMBZ2jYTuu6utCHjZFM"
    os.environ["GOOGLE_API_KEY"] = api_key
    
    print("=" * 80)
    print("🔑 Testing Google Gemini API Key")
    print("=" * 80)
    print(f"API Key: {api_key[:20]}...{api_key[-10:]}")
    print()
    
    try:
        # Test with LiteLLM (used by CrewAI)
        print("📦 Testing with LiteLLM (CrewAI's LLM interface)...")
        from litellm import completion
        
        # Test models
        models_to_test = [
            "gemini/gemini-2.0-flash",
            "gemini/gemini-1.5-flash",
            "gemini/gemini-pro",
        ]
        
        for model in models_to_test:
            print(f"\n🧪 Testing model: {model}")
            try:
                response = completion(
                    model=model,
                    messages=[{"role": "user", "content": "Say 'API key works!' in one sentence."}],
                    max_tokens=50,
                    api_key=api_key
                )
                
                content = response.choices[0].message.content
                print(f"   ✅ SUCCESS: {content}")
                
            except Exception as e:
                error_msg = str(e)
                print(f"   ❌ FAILED: {error_msg}")
                
                # Provide specific guidance based on error
                if "API key not valid" in error_msg or "invalid" in error_msg.lower():
                    print(f"   ⚠️  API key is invalid or not properly configured")
                elif "404" in error_msg or "not found" in error_msg.lower():
                    print(f"   ⚠️  Model '{model}' not available or API not enabled")
                elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                    print(f"   ⚠️  Rate limit or quota exceeded")
                elif "permission" in error_msg.lower() or "403" in error_msg:
                    print(f"   ⚠️  API key doesn't have permission for this model")
        
        print("\n" + "=" * 80)
        print("✅ API Key Test Complete")
        print("=" * 80)
        
    except ImportError as e:
        print(f"❌ Failed to import required libraries: {e}")
        print("   Make sure litellm is installed: pip install litellm")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_google_api_key()
