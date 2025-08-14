"""
Mandatory Image Injector - Ensures every blog has 2-3 images

This module automatically adds missing images to blog content when agents
fail to follow the image requirements, preventing blogs with insufficient visuals.
"""

import re
import logging
from typing import List, Tuple
from .tools.unsplash_tool import UnsplashImageTool
from .tools.openai_image_tool import OpenAIImageTool

logger = logging.getLogger(__name__)


class MandatoryImageInjector:
    """
    Ensures every blog has 2-3 images by automatically adding missing images
    when agents fail to follow image requirements.
    """
    
    def __init__(self):
        self.unsplash_tool = UnsplashImageTool()
        self.openai_tool = OpenAIImageTool()
    
    def ensure_adequate_images(self, content: str, topic: str) -> str:
        """
        Ensure blog content has 2-3 images, adding missing ones if necessary.
        
        Args:
            content: The blog content to check and potentially modify
            topic: The blog topic for generating relevant images
            
        Returns:
            Modified content with adequate images
        """
        # Count existing images
        existing_images = self._count_images(content)
        
        logger.info(f"Blog has {existing_images} images, checking adequacy...")
        
        # If we have adequate images (2-3), return as-is
        if 2 <= existing_images <= 3:
            logger.info("✅ Blog has adequate images")
            return content
        
        # If too many images, log warning but don't remove
        if existing_images > 3:
            logger.warning(f"⚠️ Blog has {existing_images} images (more than recommended 3)")
            return content
        
        # If insufficient images (0-1), add missing ones
        images_needed = 2 - existing_images
        logger.warning(f"❌ Blog has insufficient images ({existing_images}), adding {images_needed} images")
        
        return self._inject_missing_images(content, topic, images_needed, existing_images)
    
    def _count_images(self, content: str) -> int:
        """Count images in markdown content"""
        pattern = r'!\[([^\]]*)\]\(([^)]+)(?:\s+"([^"]*)")?\)'
        matches = re.findall(pattern, content)
        return len(matches)
    
    def _inject_missing_images(self, content: str, topic: str, images_needed: int, existing_count: int) -> str:
        """Inject missing images into the content"""
        modified_content = content
        
        # Split content into sections for strategic placement
        sections = self._split_into_sections(content)
        
        for i in range(images_needed):
            image_number = existing_count + i + 1
            
            # Generate image based on position
            if image_number == 1:
                # Hero image - try Unsplash first
                image_markdown = self._generate_hero_image(topic)
                modified_content = self._insert_hero_image(modified_content, image_markdown)
            else:
                # Supporting image - mix of Unsplash and AI
                use_ai = (i % 2 == 1)  # Alternate between Unsplash and AI
                image_markdown = self._generate_supporting_image(topic, image_number, use_ai)
                modified_content = self._insert_supporting_image(modified_content, image_markdown, sections)
        
        logger.info(f"✅ Successfully injected {images_needed} images")
        return modified_content
    
    def _generate_hero_image(self, topic: str) -> str:
        """Generate a hero image for the blog topic using intelligent selection."""
        logger.info(f"Generating hero image for topic: {topic}")
        
        # Create a focused query for hero images
        hero_query = f"{topic} professional overview"
        
        # The enhanced Unsplash tool will automatically fall back to AI if no relevant images
        try:
            result = self.unsplash_tool._run(hero_query, count=1)
            
            # Check if it's a placeholder (fallback case)
            if "placeholder" in result.lower() or "placehold" in result.lower():
                logger.warning("Hero image generation fell back to placeholder")
                return self._create_fallback_image(topic, "hero")
            
            logger.info("✅ Generated hero image (Unsplash or AI)")
            return result
            
        except Exception as e:
            logger.error(f"Hero image generation failed: {e}")
            return self._create_fallback_image(topic, "hero")
    
    def _generate_supporting_image(self, topic: str, image_number: int, use_ai: bool = False) -> str:
        """Generate a supporting image using intelligent selection."""
        logger.info(f"Generating supporting image #{image_number} for topic: {topic}")
        
        # Create more specific queries for supporting images
        supporting_queries = [
            f"{topic} technology implementation",
            f"{topic} business application", 
            f"{topic} team collaboration",
            f"{topic} data visualization"
        ]
        query = supporting_queries[(image_number - 2) % len(supporting_queries)]
        
        # The enhanced Unsplash tool will automatically decide Unsplash vs AI
        try:
            result = self.unsplash_tool._run(query, count=1)
            
            # Check if it's a placeholder (fallback case)
            if "placeholder" in result.lower() or "placehold" in result.lower():
                logger.warning(f"Supporting image #{image_number} fell back to placeholder")
                return self._create_fallback_image(topic, f"supporting-{image_number}")
            
            logger.info(f"✅ Generated supporting image #{image_number} (Unsplash or AI)")
            return result
            
        except Exception as e:
            logger.error(f"Supporting image #{image_number} generation failed: {e}")
            return self._create_fallback_image(topic, f"supporting-{image_number}")
    
    def _insert_hero_image(self, content: str, image_markdown: str) -> str:
        """Insert hero image after the introduction"""
        lines = content.split('\n')
        
        # Find the end of the introduction (after first few paragraphs)
        insertion_point = self._find_intro_end(lines)
        
        # Insert the image
        lines.insert(insertion_point, "")
        lines.insert(insertion_point + 1, image_markdown.strip())
        lines.insert(insertion_point + 2, "")
        
        return '\n'.join(lines)
    
    def _insert_supporting_image(self, content: str, image_markdown: str, sections: List[str]) -> str:
        """Insert supporting image in appropriate section"""
        lines = content.split('\n')
        
        # Find a good insertion point (between sections)
        insertion_points = self._find_section_boundaries(lines)
        
        if insertion_points:
            # Use middle sections for supporting images
            mid_point = insertion_points[len(insertion_points) // 2]
            lines.insert(mid_point, "")
            lines.insert(mid_point + 1, image_markdown.strip())
            lines.insert(mid_point + 2, "")
        else:
            # Fallback: insert in middle of content
            mid_line = len(lines) // 2
            lines.insert(mid_line, "")
            lines.insert(mid_line + 1, image_markdown.strip())
            lines.insert(mid_line + 2, "")
        
        return '\n'.join(lines)
    
    def _find_intro_end(self, lines: List[str]) -> int:
        """Find the end of the introduction section"""
        paragraph_count = 0
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith('#'):
                if i > 0 and lines[i-1].strip() == '':
                    paragraph_count += 1
                    if paragraph_count >= 2:  # After 2 paragraphs
                        return i + 1
        
        # Fallback: after first header
        for i, line in enumerate(lines):
            if line.startswith('##'):  # First H2
                return i
        
        # Final fallback: line 10
        return min(10, len(lines))
    
    def _find_section_boundaries(self, lines: List[str]) -> List[int]:
        """Find section boundaries (headers) for image placement"""
        boundaries = []
        for i, line in enumerate(lines):
            if line.startswith('##') and i > 0:  # H2 headers
                boundaries.append(i)
        return boundaries
    
    def _split_into_sections(self, content: str) -> List[str]:
        """Split content into logical sections"""
        # Simple implementation - split by H2 headers
        sections = re.split(r'\n## ', content)
        return sections
    
    def _create_fallback_image(self, topic: str, image_type: str) -> str:
        """Create a fallback placeholder image"""
        alt_text = f"{topic} - {image_type}"
        placeholder_url = f"https://via.placeholder.com/800x450/4A90A4/FFFFFF?text={topic.replace(' ', '+')}"
        
        return f"""
![{alt_text}]({placeholder_url} "{alt_text}")

*Placeholder image - {topic} related visual*
"""


def create_mandatory_image_injector() -> MandatoryImageInjector:
    """Factory function to create a mandatory image injector"""
    return MandatoryImageInjector()
