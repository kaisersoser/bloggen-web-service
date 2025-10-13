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
    """Input schema for intelligent image search tool."""

    query: str = Field(
        ...,
        description="Specific, descriptive keywords for finding relevant images. Use technical terms and context (e.g., 'machine learning neural network visualization', 'cybersecurity monitoring dashboard', 'agile development team planning'). The tool will automatically choose between Unsplash photos and AI generation based on relevance.",
    )
    count: int = Field(
        default=1, description="Number of images to return (1-3 recommended)"
    )
    orientation: str = Field(
        default="landscape",
        description="Image orientation: 'landscape', 'portrait', or 'squarish'",
    )


class UnsplashImageTool(BaseTool):
    """
    Tool for searching and retrieving high-quality images from Unsplash API.

    This tool allows CrewAI agents to automatically find and insert relevant images
    into blog content by searching Unsplash's extensive collection of professional photos.
    """

    name: str = "unsplash_image_search"
    description: str = (
        "Intelligent image search that finds highly relevant, professional images for blog content. "
        "Automatically selects the best source: searches Unsplash for real photos when relevant, "
        "or generates custom AI images for abstract concepts. Uses advanced relevance scoring to ensure "
        "images directly relate to your content. Provide specific, descriptive keywords for best results "
        "(e.g., 'machine learning neural network visualization', 'cybersecurity team monitoring dashboard'). "
        "Returns properly formatted Markdown ready for blog insertion. The tool intelligently handles "
        "fallbacks to ensure you always get relevant, high-quality visuals."
    )
    args_schema: Type[BaseModel] = UnsplashSearchInput

    def __init__(self, access_key: Optional[str] = None, audit_tracker=None, **kwargs):
        """Initialize the Unsplash tool with API credentials and audit tracking."""
        super().__init__(**kwargs)

        # Store audit tracker for tracking API usage
        self._audit_tracker = audit_tracker

        # Explicitly load environment variables
        try:
            from ..helper import load_env

            load_env()
        except ImportError:
            # Fallback if helper is not available
            from dotenv import load_dotenv

            load_dotenv()

        # Store access key in a way that doesn't conflict with Pydantic
        self._access_key = access_key or os.getenv("UNSPLASH_ACCESS_KEY")
        self._base_url = "https://api.unsplash.com"

        # Add debug logging to see what's happening
        if self._access_key:
            logging.info(
                f"Unsplash tool initialized with API key: {self._access_key[:10]}..."
            )
        else:
            logging.warning(
                "Unsplash Access Key not found. Tool will return placeholder images."
            )
            logging.info(
                "Available env vars: "
                + ", ".join([k for k in os.environ.keys() if "UNSPLASH" in k])
            )

    def _run(self, query: str, count: int = 1, orientation: str = "landscape") -> str:
        """
        Search for images on Unsplash and return formatted Markdown.
        Automatically falls back to AI generation if no relevant images found.

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
            if orientation not in ["landscape", "portrait", "squarish"]:
                orientation = "landscape"

            # If no API key, return placeholder
            if not self._access_key:
                logging.info("No Unsplash API key - falling back to AI generation")
                return self._fallback_to_ai_generation(query, count, orientation)

            # Search for images
            images = self._search_unsplash_images(query, count, orientation)

            if not images:
                # No relevant images found - fallback to AI generation
                logging.info(
                    f"No relevant Unsplash images found for '{query}' - falling back to AI generation"
                )
                return self._fallback_to_ai_generation(query, count, orientation)

            # Format as Markdown
            result = self._format_images_as_markdown(images, query)
            logging.info(
                f"✅ Successfully found {len(images)} relevant Unsplash images"
            )
            return result

        except Exception as e:
            logging.error(f"Error in Unsplash image search: {str(e)}")
            # Return AI generation on any error
            logging.info("Falling back to AI generation due to error")
            return self._fallback_to_ai_generation(query, count, orientation)

    def _fallback_to_ai_generation(
        self, query: str, count: int, orientation: str
    ) -> str:
        """Fallback to AI image generation when Unsplash fails or returns irrelevant results."""
        try:
            # Import here to avoid circular imports
            from .openai_image_tool import OpenAIImageTool

            ai_tool = OpenAIImageTool(audit_tracker=self._audit_tracker)

            # Check if AI tool is available
            if not ai_tool._api_key or not ai_tool._openai_available:
                logging.warning("AI image generation not available - using placeholder")
                return self._generate_placeholder_images(query, count, orientation)

            # Generate images using AI
            results = []
            for i in range(count):
                # Create contextual prompts for AI generation with photorealistic emphasis
                if i == 0:
                    # Hero image - photorealistic and directly relevant
                    prompt = f"Photorealistic professional image of {query}, modern stylish composition, premium quality lighting, sharp focus, cinematic aesthetic, directly relevant to the topic, suitable for high-end blog header"
                else:
                    # Supporting images - still photorealistic but more informational
                    prompt = f"Photorealistic professional image illustrating {query}, modern clean style, high-quality photography, educational and informative visual representation"

                # Map orientation to size for AI generation
                size_mapping = {
                    "landscape": "1792x1024",
                    "portrait": "1024x1792",
                    "squarish": "1024x1024",
                }
                size = size_mapping.get(orientation, "1024x1024")

                ai_result = ai_tool._run(prompt=prompt, size=size, aspect=orientation)
                if ai_result and "![" in ai_result:
                    results.append(ai_result)
                    logging.info(f"✅ Generated AI image {i+1}/{count}")
                else:
                    logging.warning(f"❌ AI image generation {i+1} failed")

            if results:
                combined_result = "\n\n".join(results)
                logging.info(
                    f"✅ Successfully generated {len(results)} AI images as Unsplash fallback"
                )
                return combined_result
            else:
                # Final fallback to placeholder
                logging.warning("All AI generation attempts failed - using placeholder")
                return self._generate_placeholder_images(query, count, orientation)

        except Exception as e:
            logging.error(f"AI fallback generation failed: {str(e)}")
            return self._generate_placeholder_images(query, count, orientation)

    def _search_unsplash_images(
        self, query: str, count: int, orientation: str
    ) -> List[Dict]:
        """Search Unsplash API for images."""
        try:
            # Clean and enhance the search query
            clean_query = self._enhance_search_query(query)
            logging.info(
                f"Searching Unsplash for: '{clean_query}' (original: '{query}')"
            )

            url = f"{self._base_url}/search/photos"
            headers = {
                "Authorization": f"Client-ID {self._access_key}",
                "Accept-Version": "v1",
            }

            params = {
                "query": clean_query,
                "per_page": count,
                "orientation": orientation,
                "order_by": "relevant",
                "content_filter": "high",  # Family-friendly content
            }

            logging.debug(f"Unsplash API request: {url} with params: {params}")

            response = requests.get(url, headers=headers, params=params, timeout=10)

            # Track Unsplash API usage in audit system
            try:
                if self._audit_tracker and hasattr(
                    self._audit_tracker, "track_api_call"
                ):
                    # Estimate minimal cost for Unsplash API calls (free tier tracking)
                    self._audit_tracker.track_api_call(
                        model="unsplash_api",
                        input_tokens=len(clean_query.split()),  # Query complexity
                        output_tokens=len(response.content)
                        // 100,  # Response size estimate
                        cost=0.0,  # Unsplash has a free tier
                        phase="image_search",
                        agent_role="unsplash_image_tool",
                    )
            except Exception:
                logging.debug("Unsplash usage tracking failed", exc_info=True)

            # Log response status for debugging
            logging.info(f"Unsplash API response: {response.status_code}")

            if response.status_code == 401:
                logging.error(
                    "Unsplash API authentication failed - check UNSPLASH_ACCESS_KEY"
                )
                return []
            elif response.status_code == 403:
                logging.error("Unsplash API rate limit exceeded or access forbidden")
                return []

            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            logging.info(f"Unsplash returned {len(results)} images")

            # Validate that we have proper image data and check relevance
            valid_results = []
            for i, result in enumerate(results):
                if (
                    result.get("urls")
                    and result.get("user")
                    and any(
                        result["urls"].get(key)
                        for key in ["regular", "full", "raw", "small"]
                    )
                ):

                    # Score image relevance
                    relevance_score = self._score_image_relevance(
                        result, query, clean_query
                    )

                    if relevance_score >= 0.3:  # Minimum relevance threshold
                        valid_results.append(result)
                        logging.info(
                            f"Image {i+1} relevance score: {relevance_score:.2f} - ACCEPTED"
                        )
                    else:
                        logging.info(
                            f"Image {i+1} relevance score: {relevance_score:.2f} - REJECTED (too irrelevant)"
                        )
                else:
                    logging.warning(
                        f"Skipping invalid image result {i}: missing required fields"
                    )

            logging.info(
                f"Found {len(valid_results)} relevant images out of {len(results)} returned"
            )

            # If no images meet relevance criteria, return empty for AI fallback
            if len(valid_results) == 0 and len(results) > 0:
                logging.warning(
                    "All Unsplash images failed relevance check - triggering AI fallback"
                )
                return []
            return valid_results

        except requests.exceptions.RequestException as e:
            logging.error(f"Unsplash API request failed: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logging.error(f"Response status: {e.response.status_code}")
                try:
                    logging.error(f"Response body: {e.response.text}")
                except:
                    pass
            return []
        except Exception as e:
            logging.error(f"Unexpected error in Unsplash search: {str(e)}")
            return []

    def _enhance_search_query(self, query: str) -> str:
        """Enhance search query for better Unsplash results with intelligent keyword extraction."""
        import re

        # Comprehensive stop words for better filtering
        stop_words = {
            "blog",
            "post",
            "article",
            "content",
            "guide",
            "tutorial",
            "introduction",
            "overview",
            "summary",
            "analysis",
            "discussion",
            "exploration",
            "deep",
            "dive",
            "comprehensive",
            "ultimate",
            "complete",
            "beginner",
            "advanced",
            "tips",
            "how",
            "what",
            "why",
            "when",
            "where",
            "best",
            "practices",
            "strategy",
            "strategies",
            "method",
            "methods",
            "approach",
            "approaches",
            "way",
            "ways",
        }

        # Clean and normalize the query
        query = query.lower().strip()
        query = re.sub(r"[^\w\s-]", " ", query)  # Remove special chars except hyphens
        words = [word.strip() for word in query.split() if word.strip()]

        # Filter out stop words but keep meaningful terms
        enhanced_words = []
        for word in words:
            # Keep important technical terms even if they might be stop words
            if (
                word not in stop_words
                or len(word) > 8  # Keep longer technical terms
                or word in ["ai", "ml", "api", "ui", "ux"]
            ):  # Keep tech abbreviations
                enhanced_words.append(word)

        # If we filtered too much, keep the most important words
        if len(enhanced_words) < 2 and len(words) >= 2:
            # Keep the longest words as they're likely most specific
            enhanced_words = sorted(words, key=len, reverse=True)[:3]
        elif len(enhanced_words) == 0:
            return query  # Fallback to original

        enhanced_query = " ".join(enhanced_words)

        # Add context-specific modifiers for better visual results
        visual_modifiers = self._get_visual_modifiers(enhanced_query)
        if visual_modifiers:
            enhanced_query = f"{enhanced_query} {visual_modifiers}"

        logging.debug(f"Enhanced query: '{query}' -> '{enhanced_query}'")
        return enhanced_query

    def _get_visual_modifiers(self, query: str) -> str:
        """Add visual context modifiers based on query content."""
        query_lower = query.lower()

        # Technology-related terms get tech modifiers
        if any(
            word in query_lower
            for word in [
                "ai",
                "artificial",
                "intelligence",
                "machine",
                "learning",
                "neural",
                "algorithm",
            ]
        ):
            return "technology futuristic"
        elif any(
            word in query_lower
            for word in ["data", "analytics", "visualization", "chart", "graph"]
        ):
            return "dashboard analytics"
        elif any(
            word in query_lower
            for word in ["team", "collaboration", "meeting", "office", "workplace"]
        ):
            return "business professional"
        elif any(
            word in query_lower
            for word in ["coding", "programming", "developer", "software"]
        ):
            return "coding computer"
        elif any(
            word in query_lower
            for word in ["security", "cyber", "protection", "safety"]
        ):
            return "security protection"
        elif any(
            word in query_lower for word in ["innovation", "startup", "entrepreneur"]
        ):
            return "innovation business"

        return ""

    def _score_image_relevance(
        self, image: Dict, original_query: str, enhanced_query: str
    ) -> float:
        """Score image relevance based on metadata and search terms."""
        score = 0.0

        # Get image metadata
        alt_description = (image.get("alt_description") or "").lower()
        description = (image.get("description") or "").lower()
        tags = []
        if image.get("tags"):
            tags = [
                tag.get("title", "").lower()
                for tag in image["tags"]
                if tag.get("title")
            ]

        # Combine all text sources
        image_text = f"{alt_description} {description} {' '.join(tags)}"

        # Extract key terms from queries
        original_terms = set(original_query.lower().split())
        enhanced_terms = set(enhanced_query.lower().split())
        all_query_terms = original_terms.union(enhanced_terms)

        # Score based on direct term matches
        term_matches = 0
        for term in all_query_terms:
            if len(term) > 2 and term in image_text:  # Ignore very short terms
                term_matches += 1
                score += 0.2  # Each relevant term adds to score

        # Bonus for multiple term matches (indicates strong relevance)
        if term_matches >= 2:
            score += 0.3

        # Semantic relevance scoring
        score += self._calculate_semantic_relevance(image_text, original_query)

        # Quality indicators (downloads, likes) add minor score boost
        downloads = image.get("downloads", 0)
        likes = image.get("likes", 0)

        if downloads > 1000:  # Popular images are often more relevant
            score += 0.1
        if likes > 100:
            score += 0.05

        # Cap the score at 1.0
        return min(score, 1.0)

    def _calculate_semantic_relevance(self, image_text: str, query: str) -> float:
        """Calculate semantic relevance between image metadata and query."""
        # Simple semantic scoring based on domain-specific keyword groups
        semantic_groups = {
            "technology": [
                "tech",
                "digital",
                "computer",
                "software",
                "coding",
                "algorithm",
                "system",
            ],
            "ai_ml": [
                "artificial",
                "intelligence",
                "machine",
                "learning",
                "neural",
                "deep",
                "model",
            ],
            "business": [
                "business",
                "corporate",
                "office",
                "professional",
                "meeting",
                "team",
            ],
            "data": [
                "data",
                "analytics",
                "chart",
                "graph",
                "visualization",
                "dashboard",
            ],
            "security": ["security", "cyber", "protection", "safe", "secure", "lock"],
            "innovation": [
                "innovation",
                "creative",
                "idea",
                "startup",
                "entrepreneur",
                "future",
            ],
        }

        query_lower = query.lower()
        semantic_score = 0.0

        for group_name, keywords in semantic_groups.items():
            # Check if query belongs to this semantic group
            query_matches = sum(1 for keyword in keywords if keyword in query_lower)
            if query_matches > 0:
                # Check if image metadata contains related terms
                image_matches = sum(1 for keyword in keywords if keyword in image_text)
                if image_matches > 0:
                    # Score based on how many related terms match
                    group_score = min(image_matches / len(keywords), 0.3)
                    semantic_score += group_score

        return semantic_score

    def _format_images_as_markdown(self, images: List[Dict], query: str) -> str:
        """Format Unsplash images as Markdown with proper attribution."""
        if not images:
            return ""

        markdown_images = []

        for i, image in enumerate(images):
            try:
                # Validate image data structure
                if not image.get("urls") or not image.get("user"):
                    logging.warning(
                        f"Invalid image data structure from Unsplash API for image {i}"
                    )
                    continue

                # Get image details with fallbacks
                image_url = (
                    image["urls"].get("regular")
                    or image["urls"].get("full")
                    or image["urls"].get("raw")
                    or image["urls"].get("small")
                )

                if not image_url:
                    logging.warning(
                        f"No valid image URL found in Unsplash response for image {i}"
                    )
                    continue

                # Validate URL format
                if not image_url.startswith(("http://", "https://")):
                    logging.warning(f"Invalid image URL format: {image_url}")
                    continue

                alt_text = (
                    image.get("alt_description", "")
                    or image.get("description", "")
                    or f"Image related to {query}"
                )
                photographer = image["user"].get("name", "Unknown photographer")
                photographer_url = image["user"].get("links", {}).get("html", "#")
                photo_url = image.get("links", {}).get("html", "#")

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

            except (KeyError, TypeError) as e:
                logging.error(f"Error processing Unsplash image {i}: {str(e)}")
                logging.debug(f"Image data: {image}")
                continue

        if not markdown_images:
            logging.warning("No valid images could be processed from Unsplash response")
            return self._generate_placeholder_images(query, 1, "landscape")

        return "\n\n".join(markdown_images)

    def _clean_alt_text(self, alt_text: str, query: str) -> str:
        """Clean and improve alt text for accessibility."""
        if not alt_text or len(alt_text.strip()) < 5:
            # Generate descriptive alt text from query
            return f"Professional image showcasing {query}"

        # Clean up the alt text
        alt_text = re.sub(
            r"[^\w\s-]", " ", alt_text
        )  # Remove special chars except hyphens
        alt_text = " ".join(alt_text.split())  # Normalize whitespace

        # Ensure it's not too long
        if len(alt_text) > 100:
            alt_text = alt_text[:97] + "..."

        return alt_text

    def _generate_placeholder_images(
        self, query: str, count: int, orientation: str
    ) -> str:
        """Generate placeholder images when Unsplash is unavailable."""
        placeholders = []

        # Map orientation to dimensions for placeholder service
        dimensions = {
            "landscape": "800x450",
            "portrait": "600x800",
            "squarish": "600x600",
        }

        size = dimensions.get(orientation, "800x450")

        # Clean query for URL encoding
        clean_query = query.replace(" ", "+").replace(",", "+")

        for i in range(count):
            # Use placeholder.com as it's more reliable than deprecated Unsplash source API
            placeholder_url = (
                f"https://via.placeholder.com/{size}/4A90A4/FFFFFF?text={clean_query}"
            )
            alt_text = f"Placeholder image for {query}"

            if count == 1:
                markdown = f"""
![{alt_text}]({placeholder_url} "{alt_text}")

*Placeholder image - Unsplash API unavailable*
"""
            else:
                markdown = f"""
![{alt_text}]({placeholder_url} "{alt_text}")
*Placeholder image - Unsplash API unavailable*
"""

            placeholders.append(markdown.strip())

        return "\n\n".join(placeholders)


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
