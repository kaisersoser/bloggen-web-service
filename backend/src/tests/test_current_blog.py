#!/usr/bin/env python3
"""
Quick test to check if the issue is with the frontend endpoint or flow execution
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bloggen.content_validator import ContentValidator

def test_current_blog():
    """Test the current generated blog for deprecated sources"""
    blog_path = "/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/generated_blogs/blog.md"
    
    try:
        with open(blog_path, 'r') as f:
            content = f.read()
        
        print("🔍 ANALYZING CURRENT GENERATED BLOG")
        print("=" * 60)
        
        # Check content length
        print(f"📊 Content length: {len(content)} characters")
        
        # Validate images
        validator = ContentValidator()
        validation_result = validator.validate_content(content)
        
        print(f"\n🖼️ IMAGE ANALYSIS:")
        print(f"   📸 Total Images: {validation_result['total_images']}")
        print(f"   ✅ Valid Images: {validation_result['valid_images']}")
        print(f"   ❌ Deprecated Images: {validation_result['deprecated_images']}")
        print(f"   🎯 Overall Valid: {validation_result['valid']}")
        
        if validation_result['issues']:
            print(f"\n🚨 ISSUES FOUND:")
            for i, issue in enumerate(validation_result['issues'], 1):
                print(f"   {i}. {issue}")
        
        if validation_result['suggestions']:
            print(f"\n� SUGGESTIONS:")
            for i, suggestion in enumerate(validation_result['suggestions'], 1):
                print(f"   {i}. {suggestion}")
        
        # Show content preview
        print(f"\n📝 Content Preview (first 500 chars):")
        print("-" * 60)
        print(content[:500])
        print("-" * 60)
        
        return content, validation_result
        
    except Exception as e:
        print(f"❌ Error reading blog: {e}")
        return None, {}

if __name__ == "__main__":
    test_current_blog()
