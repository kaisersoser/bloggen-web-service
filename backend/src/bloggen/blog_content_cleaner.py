"""
Blog Content Post-Processor - Cleans finalization output to remove leaked instructions.

This module provides post-processing functionality to clean blog content that may contain
leaked processing instructions or agent thoughts mixed with the actual blog content.
"""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class BlogContentCleaner:
    """
    Cleans blog content by removing leaked processing instructions and agent thoughts.

    Common issues this addresses:
    - Finalization agent instructions appearing at the beginning of blog content
    - Processing thoughts or meta-commentary mixed with blog content
    - Redundant introductory text from agents
    """

    def __init__(self):
        # Patterns that indicate leaked processing instructions
        self.instruction_patterns = [
            r"^I will meticulously review.*?(?=\n#|\n\n#|Here is the finalized blog post|The finalized blog post)",
            r"^I will.*?(?:for publication\.|ready for publication:|publication:)\s*(?:\n\n)?",
            r"^Here is the finalized blog post.*?(?:\n\n)?",
            r"^The finalized blog post.*?(?:\n\n)?",
            r"^Following are the final.*?(?:\n\n)?",
            r"^Below is the polished.*?(?:\n\n)?",
            r"^I have reviewed and finalized.*?(?:\n\n)?",
            r"^After careful review.*?(?:\n\n)?",
        ]

        # Patterns for common agent meta-commentary (as separate lines)
        self.meta_commentary_lines = [
            r"^Here is the finalized blog post, ready for publication:\s*$",
            r"^The finalized blog post is ready:\s*$",
            r"^Final blog post:\s*$",
            r"^Ready for publication:\s*$",
            r"^Below is the final version:\s*$",
            r"^Here\'s the final version:\s*$",
        ]

    def clean_finalization_output(self, content: str) -> Tuple[str, List[str]]:
        """
        Clean finalization output by removing leaked instructions and meta-commentary.

        Args:
            content: Raw finalization output that may contain leaked instructions

        Returns:
            Tuple of (cleaned_content, list_of_removed_sections)
        """
        original_content = content
        removed_sections = []

        # Remove instruction patterns from the beginning
        for pattern in self.instruction_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                removed_text = match.group(0)
                content = content.replace(removed_text, "", 1).strip()
                removed_sections.append(f"Instructions: {removed_text[:100]}...")
                logger.info(f"Removed leaked instructions: {removed_text[:50]}...")

        # Remove meta-commentary lines (process line by line)
        lines = content.split("\n")
        filtered_lines = []

        for line in lines:
            is_meta_commentary = False
            for pattern in self.meta_commentary_lines:
                if re.match(pattern, line, re.IGNORECASE):
                    removed_sections.append(f"Meta-commentary: {line}")
                    logger.info(f"Removed meta-commentary line: {line}")
                    is_meta_commentary = True
                    break

            if not is_meta_commentary:
                filtered_lines.append(line)

        content = "\n".join(filtered_lines)

        # Clean up multiple newlines and ensure proper spacing
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = content.strip()

        # Ensure content starts with a proper title (# heading)
        lines = content.split("\n")
        title_found = False
        clean_lines = []

        for line in lines:
            if line.strip().startswith("# ") and not title_found:
                title_found = True
                clean_lines.append(line)
            elif title_found:
                clean_lines.append(line)
            elif line.strip() and not title_found:
                # Skip non-title content before the actual title
                logger.info(f"Skipping pre-title content: {line[:50]}...")
                removed_sections.append(f"Pre-title: {line[:50]}...")

        cleaned_content = "\n".join(clean_lines).strip()

        # Final validation - ensure we have actual blog content
        if not cleaned_content or not cleaned_content.startswith("#"):
            logger.warning("Cleaned content doesn't start with title - using original")
            return original_content, []

        if cleaned_content != original_content:
            logger.info(
                f"Blog content cleaned: removed {len(removed_sections)} problematic sections"
            )

        return cleaned_content, removed_sections

    def validate_blog_structure(self, content: str) -> bool:
        """
        Validate that the blog content has proper structure.

        Returns:
            True if content appears to be a valid blog post
        """
        if not content or not content.strip():
            return False

        # Check for title
        if not re.search(r"^#\s+.+", content, re.MULTILINE):
            return False

        # Check for reasonable content length
        if len(content.strip()) < 100:
            return False

        # Check for obvious instruction leakage
        instruction_indicators = [
            "I will meticulously review",
            "I will then standardize",
            "My next step will be",
            "Here is the finalized blog post",
        ]

        for indicator in instruction_indicators:
            if indicator in content[:500]:  # Check first 500 chars
                return False

        return True


def create_blog_content_cleaner() -> BlogContentCleaner:
    """Factory function to create a BlogContentCleaner instance."""
    return BlogContentCleaner()


def clean_blog_content(content: str) -> str:
    """
    Convenience function to clean blog content.

    Args:
        content: Raw blog content that may contain leaked instructions

    Returns:
        Cleaned blog content
    """
    cleaner = create_blog_content_cleaner()
    cleaned_content, _ = cleaner.clean_finalization_output(content)
    return cleaned_content
