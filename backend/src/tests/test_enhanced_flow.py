#!/usr/bin/env python3
# flake8: noqa
"""
Test the enhanced flow with post-processing to ensure proper image usage.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from bloggen.flows import BlogGenerationFlow
from bloggen.content_validator import ContentValidator


def test_enhanced_flow():
    """Test flow with post-processing enabled"""

    print("🧪 TESTING ENHANCED FLOW WITH POST-PROCESSING")
    print("=" * 60)

    # Create flow with specific parameters
    flow = BlogGenerationFlow(
        user_id="test_user",
        blog_id="test_blog_enhanced",
        topic="Best AI Tools for Content Creation",
        current_year=2025,
    )

    try:
        print("🚀 Starting enhanced blog generation...")

        # Execute the flow (now with post-processing)
        result = flow.kickoff()

        print("\n✅ Flow completed, analyzing result...")
        print(f"📊 Content length: {len(str(result))} characters")

        # Validate the result
        validator = ContentValidator()
        validation_result = validator.validate_content(str(result))

        print(f"\n🖼️ FINAL IMAGE ANALYSIS:")
        print(f"   📸 Total Images: {validation_result['total_images']}")
        print(f"   ✅ Valid Images: {validation_result['valid_images']}")
        print(f"   ❌ Deprecated Images: {validation_result['deprecated_images']}")
        print(f"   🎯 Overall Valid: {validation_result['valid']}")

        if validation_result["issues"]:
            print(f"\n🚨 ISSUES FOUND:")
            for i, issue in enumerate(validation_result["issues"], 1):
                print(f"   {i}. {issue}")
        else:
            print(f"\n✅ NO ISSUES FOUND!")

        if validation_result["suggestions"]:
            print(f"\n💡 SUGGESTIONS:")
            for i, suggestion in enumerate(validation_result["suggestions"], 1):
                print(f"   {i}. {suggestion}")

        # Show content preview
        result_str = str(result)
        print(f"\n📝 Content Preview (first 1000 chars):")
        print("-" * 60)
        print(result_str[:1000])
        print("-" * 60)

        # Look for images in content
        import re

        image_pattern = r"!\[.*?\]\((.*?)\)"
        images = re.findall(image_pattern, result_str)
        if images:
            print(f"\n🖼️ Images found in content:")
            for i, url in enumerate(images, 1):
                print(f"   {i}. {url}")

        return result_str, validation_result

    except Exception as e:
        print(f"❌ Flow execution failed: {e}")
        import traceback

        traceback.print_exc()
        return None, {}


if __name__ == "__main__":
    test_enhanced_flow()
