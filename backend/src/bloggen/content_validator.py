"""
Content validation system to enforce proper image tool usage.
"""
import re
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class ContentValidator:
    """Validates blog content to ensure proper tool usage and no deprecated sources."""
    
    DEPRECATED_IMAGE_PATTERNS = [
        r'https://source\.unsplash\.com/',
        r'source\.unsplash\.com',
        r'unsplash\.com/featured',
    ]
    
    VALID_IMAGE_PATTERNS = [
        r'https://images\.unsplash\.com/',
        r'https://oaidalleapiprodscus\.blob\.core\.windows\.net/',
        r'https://placehold\.co/',
    ]
    
    @classmethod
    def validate_content(cls, content: str) -> Dict[str, Any]:
        """
        Validate blog content for proper image usage.
        
        Returns validation results with issues and suggestions.
        """
        issues = []
        suggestions = []
        
        # Find all image URLs in markdown format
        image_pattern = r'!\[.*?\]\((.*?)\)'
        image_urls = re.findall(image_pattern, content)
        total_images = len(image_urls)
        
        # Categorize images
        deprecated_images = set()
        valid_images = set()
        
        for url in image_urls:
            is_deprecated = False
            is_valid = False
            
            # Check if deprecated
            for pattern in cls.DEPRECATED_IMAGE_PATTERNS:
                if re.search(pattern, url, re.IGNORECASE):
                    deprecated_images.add(url)
                    is_deprecated = True
                    break
            
            # Check if valid (only if not deprecated)
            if not is_deprecated:
                for pattern in cls.VALID_IMAGE_PATTERNS:
                    if re.search(pattern, url, re.IGNORECASE):
                        valid_images.add(url)
                        is_valid = True
                        break
        
        deprecated_count = len(deprecated_images)
        valid_count = len(valid_images)
        
        # Generate issues
        if deprecated_count > 0:
            issues.append(f"Found {deprecated_count} deprecated image URLs")
            for url in deprecated_images:
                issues.append(f"  - {url}")
        
        # Generate suggestions
        if deprecated_count > 0:
            suggestions.append("Replace deprecated image sources with proper tool-generated images")
            suggestions.append("Use unsplash_image_search or openai_image_generate tools")
        
        if total_images == 0:
            suggestions.append("Add images using the provided image tools")
        elif valid_count == 0 and total_images > 0:
            suggestions.append("All images appear to be from invalid sources - use proper tools")
        
        validation_result = {
            'valid': deprecated_count == 0 and valid_count > 0,
            'total_images': total_images,
            'deprecated_images': deprecated_count,
            'valid_images': valid_count,
            'issues': issues,
            'suggestions': suggestions
        }
        
        return validation_result
    
    @classmethod
    def clean_deprecated_images(cls, content: str) -> str:
        """
        Remove deprecated image URLs from content.
        
        This is a fallback to clean content when agents ignore instructions.
        """
        cleaned_content = content
        
        # Remove deprecated image markdown blocks
        for pattern in cls.DEPRECATED_IMAGE_PATTERNS:
            # Remove full image markdown blocks containing deprecated URLs
            deprecated_image_pattern = rf'!\[.*?\]\([^)]*{pattern}[^)]*\)[^\n]*(?:\n\*[^\n]*\*)?'
            cleaned_content = re.sub(deprecated_image_pattern, '', cleaned_content, flags=re.IGNORECASE | re.MULTILINE)
        
        # Clean up extra newlines
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
        
        return cleaned_content.strip()
    
    @classmethod
    def log_validation_results(cls, validation: Dict[str, Any], context: str = "") -> None:
        """Log validation results for debugging."""
        prefix = f"[{context}] " if context else ""
        
        if validation['valid']:
            logger.info(f"{prefix}✅ Content validation passed")
        else:
            logger.warning(f"{prefix}❌ Content validation failed")
        
        logger.info(f"{prefix}📊 Images: {validation['total_images']} total, "
                   f"{validation['valid_images']} valid, {validation['deprecated_images']} deprecated")
        
        for issue in validation['issues']:
            logger.warning(f"{prefix}⚠️  {issue}")
        
        for suggestion in validation['suggestions']:
            logger.info(f"{prefix}💡 {suggestion}")

__all__ = ['ContentValidator']
