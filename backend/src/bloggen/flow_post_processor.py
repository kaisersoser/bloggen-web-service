"""
Flow post-processor to enforce proper image usage and clean deprecated sources.
"""

import logging
from .content_validator import ContentValidator
from .tools.unsplash_tool import UnsplashImageTool

logger = logging.getLogger(__name__)


class FlowPostProcessor:
    """Post-processes flow results to ensure proper image usage."""

    @classmethod
    def process_blog_content(
        cls, content: str, topic: str = "", force_tool_usage: bool = True
    ) -> str:
        """
        Process blog content to ensure proper image usage.

        Args:
            content: Raw blog content from flow
            topic: Blog topic for fallback image generation
            force_tool_usage: Whether to force tool-generated images

        Returns:
            Cleaned and validated blog content
        """
        if not content:
            logger.warning("Empty content provided to post-processor")
            return content

        # Validate current content
        validator = ContentValidator()
        validation_result = validator.validate_content(content)

        ContentValidator.log_validation_results(validation_result, "Pre-processing")

        # If content is already valid, return as-is
        if validation_result["valid"]:
            logger.info("✅ Content already valid, no post-processing needed")
            return content

        # Clean deprecated images
        cleaned_content = validator.clean_deprecated_images(content)

        # Re-validate after cleaning
        post_clean_validation = validator.validate_content(cleaned_content)
        ContentValidator.log_validation_results(post_clean_validation, "Post-cleaning")

        # If we have no images after cleaning and force_tool_usage is enabled
        if force_tool_usage and post_clean_validation["total_images"] == 0 and topic:
            logger.info(f"🔧 Force-adding tool-generated image for topic: {topic}")
            cleaned_content = cls._add_fallback_image(cleaned_content, topic)

        # Final validation
        final_validation = validator.validate_content(cleaned_content)
        ContentValidator.log_validation_results(final_validation, "Final")

        return cleaned_content

    @classmethod
    def _add_fallback_image(cls, content: str, topic: str) -> str:
        """Add a fallback image using the UnsplashImageTool."""
        try:
            # Initialize the tool
            unsplash_tool = UnsplashImageTool()

            # Generate a search query from topic
            query = f"{topic} tools equipment"

            # Get image from tool
            image_result = unsplash_tool._run(
                query=query, count=1, orientation="landscape"
            )

            if image_result and "![" in image_result:
                # Find a good place to insert the image (after first paragraph)
                lines = content.split("\n")
                insert_position = 0

                # Look for the end of the first paragraph or intro
                for i, line in enumerate(lines):
                    if line.strip() and not line.startswith("#"):
                        # Found start of content, look for next empty line
                        for j in range(i + 1, len(lines)):
                            if not lines[j].strip():
                                insert_position = j
                                break
                        break

                if insert_position > 0:
                    lines.insert(insert_position, "")
                    lines.insert(insert_position + 1, image_result)
                    lines.insert(insert_position + 2, "")
                    content = "\n".join(lines)
                    logger.info("✅ Successfully added fallback image")
                else:
                    # Insert after title
                    content = content.replace("\n\n", f"\n\n{image_result}\n\n", 1)
                    logger.info("✅ Successfully added fallback image after title")

        except Exception as e:
            logger.warning(f"Failed to add fallback image: {e}")

        return content


__all__ = ["FlowPostProcessor"]
