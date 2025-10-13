#!/usr/bin/env python3
# flake8: noqa
"""
Test the enhanced blog generation with stronger tool enforcement.
"""
import sys
import os

sys.path.append("src")

from bloggen.flows import BlogGenerationFlow


def test_enhanced_blog_generation():
    """Test the full blog generation flow with enhanced tool enforcement."""

    print("🚀 Testing Enhanced Blog Generation with Tool Enforcement")

    try:
        # Create flow without audit tracker for simplicity
        flow = BlogGenerationFlow()

        # Test with a simple topic that should trigger image tools
        print("📝 Generating blog about 'Best DIY tools for home renovation'...")

        result = flow.kickoff(
            inputs={
                "topic": "Best DIY tools for home renovation",
                "current_year": 2025,
                "instructions": "Focus on practical tools with clear examples",
            }
        )

        print(f"\n✅ Blog generation completed!")

        # Extract final content
        if hasattr(result, "finalization_phase"):
            final_content = str(result.finalization_phase)
        elif isinstance(result, dict) and "final_blog_post" in result:
            final_content = result["final_blog_post"]
        else:
            final_content = str(result)

        # Analyze image usage
        deprecated_count = final_content.count("source.unsplash.com")
        proper_unsplash = final_content.count("images.unsplash.com")
        openai_images = final_content.count("oaidalleapiprodscus.blob.core.windows.net")
        total_images = final_content.count("![")

        print(f"\n📈 Image Analysis:")
        print(f"  - Total images: {total_images}")
        print(f"  - Deprecated source.unsplash.com: {deprecated_count}")
        print(f"  - Proper images.unsplash.com: {proper_unsplash}")
        print(f"  - OpenAI generated images: {openai_images}")
        print(f"  - Proper tool-generated images: {proper_unsplash + openai_images}")

        # Save result
        with open("enhanced_blog_fixed.md", "w") as f:
            f.write(final_content)
        print(f"\n📄 Blog saved to: enhanced_blog_fixed.md")

        # Status
        if deprecated_count > 0:
            print("❌ ISSUE: Still using deprecated image sources")
        elif proper_unsplash > 0 or openai_images > 0:
            print("✅ SUCCESS: Using proper image tools")
        else:
            print("⚠️  WARNING: No images found or different source")

        return final_content

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_enhanced_blog_generation()
