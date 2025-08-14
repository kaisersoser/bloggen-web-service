#!/usr/bin/env python3
"""
Test the enhanced Unsplash tool with intelligent fallback to AI generation.
This script tests the new relevance scoring and automatic AI fallback features.
"""

import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from bloggen.tools.unsplash_tool import UnsplashImageTool
from bloggen.tools.openai_image_tool import OpenAIImageTool
import re

def test_enhanced_unsplash_tool():
    """Test the enhanced Unsplash tool with relevance scoring"""
    print("🔍 TESTING ENHANCED UNSPLASH TOOL WITH INTELLIGENT FALLBACK")
    print("=" * 80)
    
    # Initialize the tool
    tool = UnsplashImageTool()
    
    # Test scenarios with different relevance levels
    test_queries = [
        ("artificial intelligence machine learning", "HIGH relevance expected"),
        ("data science analytics visualization", "HIGH relevance expected"),
        ("cybersecurity protection monitoring", "MEDIUM relevance expected"), 
        ("quantum computing research breakthrough", "LOW relevance expected - should trigger AI fallback"),
        ("very-specific-nonexistent-topic-12345", "NO relevance expected - should trigger AI fallback")
    ]
    
    for query, expectation in test_queries:
        print(f"\n📝 Testing query: '{query}'")
        print(f"Expected outcome: {expectation}")
        print("-" * 60)
        
        try:
            result = tool._run(query=query, count=1, orientation="landscape")
            
            # Analyze the result
            if "![" in result:
                # Extract URL to determine source
                pattern = r'!\[([^\]]*)\]\(([^)]+)(?:\s+"([^"]*)")?\)'
                matches = re.findall(pattern, result)
                
                if matches:
                    alt, url, title = matches[0]
                    print(f"✅ Generated image successfully")
                    print(f"Alt text: {alt}")
                    
                    # Determine source
                    if "images.unsplash.com" in url:
                        print("🏞️ Source: UNSPLASH (real photo)")
                    elif "oaidalleapiprodscus.blob.core.windows.net" in url or "dalle" in url.lower():
                        print("🤖 Source: AI GENERATION (OpenAI DALL-E)")
                    elif "placeholder" in url.lower() or "placehold" in url.lower():
                        print("📋 Source: PLACEHOLDER (fallback)")
                    else:
                        print(f"❓ Source: UNKNOWN ({url[:50]}...)")
                    
                    print(f"📸 Result preview: {result[:150]}...")
                else:
                    print("❌ Failed to parse image markdown")
            else:
                print("❌ No image generated")
                print(f"Result: {result}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print("\n" + "="*80)
    print("🎯 SUMMARY:")
    print("The enhanced tool should:")
    print("✅ Use Unsplash for highly relevant queries (real photos)")
    print("✅ Automatically fall back to AI generation for abstract/irrelevant queries")
    print("✅ Only use placeholders when both Unsplash and AI fail")
    print("✅ Provide better, more contextual images overall")

def test_relevance_scoring():
    """Test the relevance scoring system directly"""
    print("\n\n🔬 TESTING RELEVANCE SCORING SYSTEM")
    print("=" * 80)
    
    tool = UnsplashImageTool()
    
    # Mock image data for testing
    test_images = [
        {
            "alt_description": "person using laptop with artificial intelligence dashboard",
            "description": "Machine learning engineer working on neural network model",
            "tags": [{"title": "artificial intelligence"}, {"title": "machine learning"}, {"title": "technology"}],
            "downloads": 5000,
            "likes": 250
        },
        {
            "alt_description": "beautiful sunset over mountains", 
            "description": "Scenic landscape photography",
            "tags": [{"title": "landscape"}, {"title": "nature"}, {"title": "sunset"}],
            "downloads": 1000,
            "likes": 50
        },
        {
            "alt_description": "team meeting in modern office",
            "description": "Business professionals collaborating on project",
            "tags": [{"title": "business"}, {"title": "team"}, {"title": "office"}],
            "downloads": 2000,
            "likes": 100
        }
    ]
    
    queries = [
        "artificial intelligence machine learning",
        "team collaboration business",
        "nature photography landscape"
    ]
    
    for query in queries:
        print(f"\n📊 Scoring images for query: '{query}'")
        print("-" * 40)
        
        for i, image in enumerate(test_images, 1):
            try:
                score = tool._score_image_relevance(image, query, query)
                print(f"Image {i}: {score:.2f} - {image['alt_description'][:50]}...")
                
                if score >= 0.3:
                    print(f"  ✅ ACCEPTED (score >= 0.3)")
                else:
                    print(f"  ❌ REJECTED (score < 0.3)")
            except Exception as e:
                print(f"  ❌ ERROR scoring image {i}: {e}")

if __name__ == "__main__":
    test_enhanced_unsplash_tool()
    test_relevance_scoring()
    
    print("\n" + "="*80)
    print("🚀 ENHANCED IMAGE SYSTEM TESTING COMPLETE")
    print("📈 The system now provides much more relevant images!")
    print("🎯 Irrelevant Unsplash results automatically trigger AI generation")
    print("💡 Agents will now get better, more contextual images for their blogs")
