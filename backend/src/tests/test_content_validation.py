#!/usr/bin/env python3
"""
Test the content validation system to ensure it properly detects and cleans deprecated image sources.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bloggen.content_validator import ContentValidator

def test_deprecated_image_detection():
    """Test that the validator properly detects deprecated image sources."""
    
    # Content with deprecated images
    content_with_deprecated = """
# AI Trends in 2025

The future of AI looks bright.

![AI Brain](https://source.unsplash.com/800x600/?artificial-intelligence)
*A representation of artificial intelligence*

Some more content here.

![Technology](https://source.unsplash.com/featured/?technology)

And another section.

![Valid Image](https://images.unsplash.com/photo-123456?auto=format&fit=crop&w=800&q=80)
"""
    
    # Test validation
    validation = ContentValidator.validate_content(content_with_deprecated)
    
    print("=== VALIDATION RESULTS ===")
    print(f"Valid: {validation['valid']}")
    print(f"Total Images: {validation['total_images']}")
    print(f"Deprecated Images: {validation['deprecated_images']}")
    print(f"Valid Images: {validation['valid_images']}")
    print(f"Issues: {validation['issues']}")
    print(f"Suggestions: {validation['suggestions']}")
    
    # Test cleaning
    cleaned_content = ContentValidator.clean_deprecated_images(content_with_deprecated)
    
    print("\n=== CLEANED CONTENT ===")
    print(cleaned_content)
    
    # Test validation of cleaned content
    cleaned_validation = ContentValidator.validate_content(cleaned_content)
    
    print("\n=== CLEANED VALIDATION ===")
    print(f"Valid: {cleaned_validation['valid']}")
    print(f"Total Images: {cleaned_validation['total_images']}")
    print(f"Deprecated Images: {cleaned_validation['deprecated_images']}")
    print(f"Valid Images: {cleaned_validation['valid_images']}")
    
    # Assertions
    assert validation['deprecated_images'] == 2, f"Expected 2 deprecated images, got {validation['deprecated_images']}"
    assert validation['valid_images'] == 1, f"Expected 1 valid image, got {validation['valid_images']}"
    assert validation['total_images'] == 3, f"Expected 3 total images, got {validation['total_images']}"
    assert not validation['valid'], "Content should be invalid due to deprecated images"
    
    # Cleaned content should have no deprecated images
    assert cleaned_validation['deprecated_images'] == 0, f"Cleaned content should have 0 deprecated images, got {cleaned_validation['deprecated_images']}"
    assert cleaned_validation['valid_images'] == 1, f"Cleaned content should have 1 valid image, got {cleaned_validation['valid_images']}"
    
    print("\n✅ All validation tests passed!")

def test_valid_content():
    """Test content that should pass validation."""
    
    valid_content = """
# AI Trends in 2025

The future of AI looks bright.

![AI Concept](https://images.unsplash.com/photo-123456?auto=format&fit=crop&w=800&q=80)
*A representation of artificial intelligence*

![Generated Image](https://oaidalleapiprodscus.blob.core.windows.net/private/org-123/image.png)
*AI-generated illustration*
"""
    
    validation = ContentValidator.validate_content(valid_content)
    
    print("\n=== VALID CONTENT TEST ===")
    print(f"Valid: {validation['valid']}")
    print(f"Total Images: {validation['total_images']}")
    print(f"Deprecated Images: {validation['deprecated_images']}")
    print(f"Valid Images: {validation['valid_images']}")
    
    assert validation['valid'], "Valid content should pass validation"
    assert validation['deprecated_images'] == 0, "Valid content should have no deprecated images"
    assert validation['valid_images'] == 2, f"Expected 2 valid images, got {validation['valid_images']}"
    
    print("✅ Valid content test passed!")

if __name__ == "__main__":
    print("Testing Content Validation System...")
    test_deprecated_image_detection()
    test_valid_content()
    print("\n🎉 All content validation tests completed successfully!")
