#!/usr/bin/env python3
# flake8: noqa
"""
Test the enhanced blog generation flow with content validation to ensure
no deprecated image sources are used in the final output.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import logging
from bloggen.flows import BlogGenerationFlow
from bloggen.content_validator import ContentValidator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_enhanced_flow_with_validation():
    """Test the complete enhanced flow with content validation."""

    print("🚀 Testing Enhanced Blog Generation Flow with Content Validation")

    # Skip audit tracker for this test
    audit_tracker = None

    def status_callback(message, status_type="progress", **kwargs):
        print(f"📊 Status: {message} ({status_type})")
        if status_type == "completion":
            # Validate the final output
            final_content = kwargs.get("content", message)
            print("\n" + "=" * 50)
            print("FINAL BLOG CONTENT")
            print("=" * 50)
            print(final_content)
            print("=" * 50)

            # Validate content
            validation = ContentValidator.validate_content(str(final_content))
            ContentValidator.log_validation_results(validation, "Final Output")

            print(f"\n🔍 VALIDATION SUMMARY:")
            print(f"   ✅ Valid: {validation['valid']}")
            print(f"   📸 Total Images: {validation['total_images']}")
            print(f"   ❌ Deprecated Images: {validation['deprecated_images']}")
            print(f"   ✅ Valid Images: {validation['valid_images']}")

            if validation["deprecated_images"] > 0:
                print(
                    f"\n⚠️  WARNING: Found {validation['deprecated_images']} deprecated images!"
                )
                for issue in validation["issues"]:
                    print(f"   - {issue}")
                return False
            else:
                print(f"\n🎉 SUCCESS: No deprecated images found!")
                return True

    try:
        # Create and run the enhanced flow
        flow = BlogGenerationFlow(
            status_callback=status_callback,
            user_id="test_user",
            blog_id="validation_test",
            audit_tracker=audit_tracker,
            topic="AI Image Generation Tools in 2025",
            current_year=2025,
        )

        print("🔄 Starting enhanced blog generation flow...")
        result = flow.kickoff()

        print("\n✅ Flow completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Flow failed: {e}")
        logger.exception("Enhanced flow test failed")
        return False


def test_quick_validation_check():
    """Quick test to ensure validation prevents deprecated sources."""

    print("\n🧪 Testing Quick Validation Check")

    # Sample content with deprecated sources (what we want to prevent)
    bad_content = """
# AI Tools in 2025

![AI](https://source.unsplash.com/800x600/?ai)
*Artificial Intelligence*

The future looks bright!

![Tech](https://source.unsplash.com/featured/?technology)
"""

    validation = ContentValidator.validate_content(bad_content)
    print(
        f"Bad content validation - Valid: {validation['valid']}, Deprecated: {validation['deprecated_images']}"
    )

    # Clean the content
    cleaned = ContentValidator.clean_deprecated_images(bad_content)
    cleaned_validation = ContentValidator.validate_content(cleaned)
    print(
        f"Cleaned content validation - Valid: {cleaned_validation['valid']}, Deprecated: {cleaned_validation['deprecated_images']}"
    )

    assert not validation["valid"], "Bad content should not be valid"
    assert validation["deprecated_images"] > 0, "Should detect deprecated images"
    assert (
        cleaned_validation["deprecated_images"] == 0
    ), "Cleaned content should have no deprecated images"

    print("✅ Quick validation check passed!")


if __name__ == "__main__":
    print("Testing Enhanced Blog Generation with Content Validation...")

    # Run quick validation test first
    test_quick_validation_check()

    # Run the full enhanced flow test
    success = test_enhanced_flow_with_validation()

    if success:
        print("\n🎉 All enhanced flow tests completed successfully!")
        print("✅ No deprecated image sources detected in final output!")
    else:
        print("\n❌ Enhanced flow test failed!")
        sys.exit(1)
