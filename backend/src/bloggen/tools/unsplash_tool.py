"""
Unsplash Integration Tool for CrewAI

This tool integrates with the Unsplash API to search for relevant images
based on keywords and content context, automatically generating properly
formatted Markdown image syntax for blog posts.
"""

import os
import requests
import re
from typing import Type, List, Dict, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import logging


class UnsplashSearchInput(BaseModel):
    """Input schema for Unsplash image search tool."""
    query: str = Field(..., description="Search keywords for finding relevant images (e.g., 'artificial intelligence', 'data science', 'technology')")
    count: int = Field(default=1, description="Number of images to return (1-3 recommended)")
    orientation: str = Field(default="landscape", description="Image orientation: 'landscape', 'portrait', or 'squarish'")


class UnsplashImageTool(BaseTool):
    """
    Tool for searching and retrieving high-quality images from Unsplash API.
    
    This tool allows CrewAI agents to automatically find and insert relevant images
    into blog content by searching Unsplash's extensive collection of professional photos.
    """
    
    name: str = "unsplash_image_search"
    description: str = (
        "Search for high-quality, professional images from Unsplash to enhance blog content. "
        "Provide relevant keywords describing the image you need (e.g., 'artificial intelligence robot', "
        "'data visualization charts', 'team collaboration'). The tool returns properly formatted "
        "Markdown image syntax ready to insert into blog posts. Always use descriptive keywords "
        "that match your content topic for best results."
    )
    args_schema: Type[BaseModel] = UnsplashSearchInput
    
    def __init__(self, access_key: Optional[str] = None, **kwargs):
        """Initialize the Unsplash tool with API credentials."""
        super().__init__(**kwargs)
        
        # Explicitly load environment variables
        try:
            from ..helper import load_env
            load_env()
        except ImportError:
            # Fallback if helper is not available
            from dotenv import load_dotenv
            load_dotenv()
        
        # Store access key in a way that doesn't conflict with Pydantic
        self._access_key = access_key or os.getenv('UNSPLASH_ACCESS_KEY')
        self._base_url = "https://api.unsplash.com"
        
        # Add debug logging to see what's happening
        if self._access_key:
            logging.info(f"Unsplash tool initialized with API key: {self._access_key[:10]}...")
        else:
            logging.warning("Unsplash Access Key not found. Tool will return placeholder images.")
            logging.info("Available env vars: " + ", ".join([k for k in os.environ.keys() if 'UNSPLASH' in k]))
    
    def _run(self, query: str, count: int = 1, orientation: str = "landscape") -> str:
        """
        Search for images on Unsplash and return formatted Markdown.
        
        Args:
            query (str): Search keywords for images
            count (int): Number of images to return (1-3)
            orientation (str): Image orientation preference
            
        Returns:
            str: Formatted Markdown image syntax ready for blog insertion
        """
        try:
            # Validate inputs
            count = max(1, min(count, 3))  # Limit to 1-3 images
            if orientation not in ['landscape', 'portrait', 'squarish']:
                orientation = 'landscape'
            
            # If no API key, return placeholder
            if not self._access_key:
                return self._generate_placeholder_images(query, count, orientation)
            
            # Search for images
            images = self._search_unsplash_images(query, count, orientation)
            
            if not images:
                # Fallback to placeholder if no results
                return self._generate_placeholder_images(query, count, orientation)
            
            # Format as Markdown
            return self._format_images_as_markdown(images, query)
            
        except Exception as e:
            logging.error(f"Error in Unsplash image search: {str(e)}")
            # Return placeholder on any error
            return self._generate_placeholder_images(query, count, orientation)
    
    def _search_unsplash_images(self, query: str, count: int, orientation: str) -> List[Dict]:
        """Search Unsplash API for images."""
        try:
            # Clean and enhance the search query
            clean_query = self._enhance_search_query(query)
            
            url = f"{self._base_url}/search/photos"
            headers = {
                'Authorization': f'Client-ID {self._access_key}',
                'Accept-Version': 'v1'
            }
            
            params = {
                'query': clean_query,
                'per_page': count,
                'orientation': orientation,
                'order_by': 'relevant',
                'content_filter': 'high'  # Family-friendly content
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('results', [])
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Unsplash API request failed: {str(e)}")
            return []
        except Exception as e:
            logging.error(f"Unexpected error in Unsplash search: {str(e)}")
            return []
    
    def _enhance_search_query(self, query: str) -> str:
        """Enhance search query for better Unsplash results."""
        # Remove common blog/content words that don't help image search
        stop_words = ['blog', 'post', 'article', 'content', 'guide', 'tutorial', 'introduction']
        
        # Clean the query
        words = query.lower().split()
        enhanced_words = [word for word in words if word not in stop_words]
        
        # If query is too short, keep original
        if len(enhanced_words) < 2:
            return query
        
        return ' '.join(enhanced_words)
    
    def _format_images_as_markdown(self, images: List[Dict], query: str) -> str:
        """Format Unsplash images as Markdown with proper attribution."""
        if not images:
            return ""
        
        markdown_images = []
        
        for i, image in enumerate(images):
            try:
                # Get image details
                image_url = image['urls']['regular']  # Good quality, reasonable size
                alt_text = image.get('alt_description', '') or image.get('description', '') or f"Image related to {query}"
                photographer = image['user']['name']
                photographer_url = image['user']['links']['html']
                photo_url = image['links']['html']
                
                # Clean alt text
                alt_text = self._clean_alt_text(alt_text, query)
                
                # Create Markdown with attribution
                if len(images) == 1:
                    # Single image - center it nicely
                    markdown = f"""
![{alt_text}]({image_url} "{alt_text}")

*Photo by [{photographer}]({photographer_url}) on [Unsplash]({photo_url})*
"""
                else:
                    # Multiple images - simpler format
                    markdown = f"""
![{alt_text}]({image_url} "{alt_text}")
*Photo by [{photographer}]({photographer_url}) on Unsplash*
"""
                
                markdown_images.append(markdown.strip())
                
            except KeyError as e:
                logging.error(f"Missing expected field in Unsplash response: {str(e)}")
                continue
        
        return '\n\n'.join(markdown_images)
    
    def _clean_alt_text(self, alt_text: str, query: str) -> str:
        """Clean and improve alt text for accessibility."""
        if not alt_text or len(alt_text.strip()) < 5:
            # Generate descriptive alt text from query
            return f"Professional image showcasing {query}"
        
        # Clean up the alt text
        alt_text = re.sub(r'[^\w\s-]', ' ', alt_text)  # Remove special chars except hyphens
        alt_text = ' '.join(alt_text.split())  # Normalize whitespace
        
        # Ensure it's not too long
        if len(alt_text) > 100:
            alt_text = alt_text[:97] + "..."
        
        return alt_text
    
    def _generate_placeholder_images(self, query: str, count: int, orientation: str) -> str:
        """Generate placeholder images when Unsplash is unavailable."""
        # Use Unsplash Source API as fallback (doesn't require auth)
        placeholders = []
        
        # Map orientation to dimensions
        dimensions = {
            'landscape': '800x450',
            'portrait': '600x800', 
            'squarish': '600x600'
        }
        
        size = dimensions.get(orientation, '800x450')
        
        # Generate search terms for placeholder
        search_terms = query.replace(' ', ',')
        
        for i in range(count):
            placeholder_url = f"https://source.unsplash.com/{size}/?{search_terms}"
            alt_text = f"Professional image related to {query}"
            
            if count == 1:
                markdown = f"""
![{alt_text}]({placeholder_url} "{alt_text}")

*Image from Unsplash*
"""
            else:
                markdown = f"""
![{alt_text}]({placeholder_url} "{alt_text}")
*Image from Unsplash*
"""
            
            placeholders.append(markdown.strip())
        
        return '\n\n'.join(placeholders)


# Tool factory function for easy instantiation
def create_unsplash_tool(access_key: Optional[str] = None) -> UnsplashImageTool:
    """
    Factory function to create an Unsplash tool instance.
    
    Args:
        access_key (str): Unsplash API access key
        
    Returns:
        UnsplashImageTool: Configured tool instance
    """
    return UnsplashImageTool(access_key=access_key)
