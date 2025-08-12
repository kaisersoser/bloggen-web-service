#!/usr/bin/env python3
"""
Simple test script for enhanced image integration.
"""
import sys
import os
sys.path.append('src')

from bloggen.flows import BlogGenerationFlow

def test_enhanced_image_flow():
    """Test the enhanced blog generation flow with parallel images."""
    
    print("🚀 Testing Enhanced Image Integration Flow (Simple)")
    
    try:
        # Create flow without audit tracker (simplified test)
        flow = BlogGenerationFlow()
        
        # Test with a simple AI topic
        print("📝 Generating blog about 'AI automation tools for 2025'...")
        
        result = flow.kickoff(
            inputs={
                "topic": "AI automation tools for 2025",
                "current_year": 2025,
                "instructions": "Focus on practical tools and include specific examples"
            }
        )
        
        print(f"\n✅ Blog generation completed!")
        print(f"📊 Result type: {type(result)}")
        
        if hasattr(result, 'final_blog_post'):
            final_content = result.final_blog_post
        elif isinstance(result, dict) and 'final_blog_post' in result:
            final_content = result['final_blog_post']
        else:
            final_content = str(result)
        
        # Check for image integration
        unsplash_images = final_content.count("images.unsplash.com")
        openai_images = final_content.count("oaidalleapiprodscus.blob.core.windows.net")
        deprecated_images = final_content.count("source.unsplash.com")
        total_images = final_content.count("![")
        
        print(f"\n📈 Image Integration Analysis:")
        print(f"  - Total images found: {total_images}")
        print(f"  - Unsplash API images: {unsplash_images}")
        print(f"  - OpenAI generated images: {openai_images}")
        print(f"  - Deprecated image sources: {deprecated_images}")
        print(f"  - Total proper images: {unsplash_images + openai_images}")
        
        # Save result for inspection
        with open("enhanced_blog_test_result.md", "w") as f:
            f.write(final_content)
        print(f"\n📄 Full blog saved to: enhanced_blog_test_result.md")
        
        # Show first 500 characters
        print(f"\n📖 Blog Preview:")
        print(f"{final_content[:500]}...")
        
        return final_content
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_enhanced_image_flow()
