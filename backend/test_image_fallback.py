#!/usr/bin/env python3
"""
Test the image fallback mechanism to ensure AI generation works when Unsplash fails.
"""

import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from bloggen.tools.unsplash_tool import UnsplashImageTool
from bloggen.tools.openai_image_tool import OpenAIImageTool

def test_unsplash_fallback():
    """Test what happens when Unsplash returns no results"""
    print("🔍 TESTING UNSPLASH FALLBACK MECHANISM")
    print("=" * 50)
    
    # Test Unsplash with a very specific query that likely returns no results
    print("1. Testing Unsplash with obscure query...")
    unsplash_tool = UnsplashImageTool()
    result = unsplash_tool._run("very-specific-nonexistent-query-12345", count=1)
    
    print(f"Unsplash result: {result[:200]}...")
    
    # Check if it's a placeholder
    if "placeholder" in result.lower() or "placehold" in result.lower():
        print("✅ Unsplash correctly returns placeholder when no results found")
    else:
        print("⚠️ Unsplash returned actual content (may have found results)")
    
    print("\n" + "-"*50)
    
    # Test OpenAI image generation
    print("2. Testing OpenAI image generation...")
    openai_tool = OpenAIImageTool()
    ai_result = openai_tool._run("artificial intelligence concept illustration", size="1024x1024")
    
    print(f"OpenAI result: {ai_result[:200]}...")
    
    # Check if it's working or placeholder
    if "placehold" in ai_result.lower():
        print("⚠️ OpenAI returning placeholder (API key issue or library missing)")
    elif ai_result.startswith("![") and "](http" in ai_result:
        print("✅ OpenAI correctly generates image URLs")
    else:
        print("❌ OpenAI tool not working properly")
    
    return True

def test_fallback_strategy():
    """Test the recommended fallback strategy"""
    print("\n🔄 TESTING FALLBACK STRATEGY")
    print("=" * 50)
    
    print("Simulating agent workflow:")
    print("1. Try Unsplash for 'technology' topic...")
    
    unsplash_tool = UnsplashImageTool()
    unsplash_result = unsplash_tool._run("technology", count=1)
    
    print(f"Unsplash result preview: {unsplash_result[:100]}...")
    
    # Check if fallback is needed
    if "placeholder" in unsplash_result.lower() or "placehold" in unsplash_result.lower():
        print("❌ Unsplash failed - triggering AI fallback...")
        
        openai_tool = OpenAIImageTool()
        fallback_result = openai_tool._run("modern technology illustration", size="1024x1024")
        
        print(f"AI fallback result: {fallback_result[:100]}...")
        
        if "placehold" in fallback_result.lower():
            print("❌ Both tools failed - this would require manual intervention")
        else:
            print("✅ AI fallback successful!")
    else:
        print("✅ Unsplash successful - no fallback needed")
        
        # Also test AI for variety
        print("2. Using AI for abstract concept...")
        openai_tool = OpenAIImageTool()
        ai_result = openai_tool._run("abstract data flow visualization", size="1024x1024")
        print(f"AI abstract result: {ai_result[:100]}...")

if __name__ == "__main__":
    print("🧪 TESTING IMAGE TOOL FALLBACK MECHANISMS")
    print("=" * 60)
    
    test_unsplash_fallback()
    test_fallback_strategy()
    
    print("\n" + "="*60)
    print("🎯 SUMMARY: Both tools tested for fallback capability")
    print("📝 Agents should use this strategy:")
    print("   1. Try unsplash_image_search first")
    print("   2. If placeholder returned, use openai_image_generate")
    print("   3. Never create manual URLs")
