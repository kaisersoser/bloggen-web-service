#!/usr/bin/env python3
"""
Focused test to debug the content generation phase specifically, 
bypassing the heavy fact-checking phase that causes rate limits.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bloggen.content_validator import ContentValidator
from bloggen.flows import BlogGenerationFlow

def test_content_generation_only():
    """Test just the content generation phase to see what images are generated."""
    print("🎯 Testing Content Generation Phase Only")
    
    try:
        # Create a flow like main.py does
        flow = BlogGenerationFlow(
            user_id="test_user_content",
            blog_id="test_blog_content", 
            topic="AI Tools for Content Creation",
            current_year=2025
        )
        
        # Manually run just the initialization and content generation phases
        print("🚀 Step 1: Initialize Flow")
        init_result = flow.initialize_flow()
        print(f"✅ Initialized: {init_result}")
        
        print("\n🚀 Step 2: Research Phase")
        research_result = flow.research_phase(init_result)
        print(f"✅ Research completed")
        
        print("\n🚀 Step 3: Content Generation Phase") 
        content_result = flow.content_generation_phase(research_result)
        print(f"✅ Content generation completed")
        
        print("\n🚀 Step 4: Content Validation Phase")
        validation_result = flow.content_validation_phase(content_result)
        print(f"✅ Content validation completed")
        
        # Extract the content
        content = validation_result.get('validated_content', '') or validation_result.get('initial_content', '')
        content_str = str(content)
        
        print(f"\n📊 Generated content length: {len(content_str)}")
        
        # Validate the content for images
        validation = ContentValidator.validate_content(content_str)
        ContentValidator.log_validation_results(validation, "Content Generation Test")
        
        print(f"\n🔍 IMAGE ANALYSIS:")
        print(f"   📸 Total Images: {validation['total_images']}")
        print(f"   ✅ Valid Images: {validation['valid_images']}")
        print(f"   ❌ Deprecated Images: {validation['deprecated_images']}")
        
        # Show content preview
        print(f"\n📝 Content Preview (first 1000 chars):")
        print("-" * 60)
        print(content_str[:1000])
        print("-" * 60)
        
        # Look for image URLs specifically
        if "![" in content_str:
            print(f"\n🖼️ Image URLs found:")
            lines = content_str.split('\n')
            for i, line in enumerate(lines):
                if "![" in line:
                    print(f"   Line {i+1}: {line.strip()}")
        else:
            print(f"\n⚠️ No image markdown found in content!")
        
        # Check for deprecated sources
        if "source.unsplash.com" in content_str:
            print(f"\n❌ DEPRECATED IMAGE SOURCES DETECTED!")
            deprecated_lines = [line for line in content_str.split('\n') if 'source.unsplash.com' in line]
            for line in deprecated_lines:
                print(f"   DEPRECATED: {line.strip()}")
        else:
            print(f"\n✅ No deprecated image sources found")
            
        return validation
        
    except Exception as e:
        print(f"❌ Content generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🧪 Focused Content Generation Debug Test")
    print("="*60)
    
    result = test_content_generation_only()
    
    if result:
        if result['valid']:
            print(f"\n🎉 SUCCESS: Content generation produced valid images!")
        else:
            print(f"\n❌ FAILURE: Content generation still has image issues!")
    else:
        print(f"\n⚠️ Test could not complete")
