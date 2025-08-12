#!/usr/bin/env python3
"""
Enhanced image enforcement to actively block deprecated image creation.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bloggen.flows import BlogGenerationFlow
from bloggen.content_validator import ContentValidator

def test_force_tool_usage():
    """Test with aggressive image enforcement"""
    
    print("🧪 TESTING AGGRESSIVE IMAGE ENFORCEMENT")
    print("=" * 60)
    
    # Create flow with very specific parameters
    flow = BlogGenerationFlow(
        user_id="test_user",
        blog_id="test_blog_123",
        topic="DIY Home Building Tools",
        current_year=2025
    )
    
    # Set explicit callback that will catch any issues
    def status_callback(step, progress, details):
        print(f"📊 {step}: {progress}% - {details}")
        
        # If we see content generation, immediately validate it
        if "content" in step.lower() and "completed" in details.lower():
            print("🔍 IMMEDIATE CONTENT VALIDATION")
    
    flow.status_callback = status_callback
    
    try:
        print("🚀 Starting blog generation with enhanced enforcement...")
        
        # Execute the flow
        result = flow.kickoff()
        
        print("\n✅ Flow completed, analyzing result...")
        
        # Validate the result
        validator = ContentValidator()
        validation_result = validator.validate_content(result)
        
        print(f"\n🖼️ FINAL IMAGE ANALYSIS:")
        print(f"   📸 Total Images: {validation_result['total_images']}")
        print(f"   ✅ Valid Images: {validation_result['valid_images']}")
        print(f"   ❌ Deprecated Images: {validation_result['deprecated_images']}")
        print(f"   🎯 Overall Valid: {validation_result['valid']}")
        
        if validation_result['issues']:
            print(f"\n🚨 ISSUES FOUND:")
            for i, issue in enumerate(validation_result['issues'], 1):
                print(f"   {i}. {issue}")
                
            # If we still have deprecated sources, apply cleaning
            print(f"\n🧹 APPLYING CONTENT CLEANING...")
            cleaned_result = validator.clean_deprecated_images(result)
            
            # Re-validate cleaned content
            cleaned_validation = validator.validate_content(cleaned_result)
            print(f"🧹 After cleaning - Valid: {cleaned_validation['valid']}")
            print(f"🧹 After cleaning - Deprecated: {cleaned_validation['deprecated_images']}")
            
            return cleaned_result, cleaned_validation
        
        return result, validation_result
        
    except Exception as e:
        print(f"❌ Flow execution failed: {e}")
        import traceback
        traceback.print_exc()
        return None, {}

if __name__ == "__main__":
    test_force_tool_usage()
