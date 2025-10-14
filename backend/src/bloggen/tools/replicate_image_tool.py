"""Replicate Image Generation Tool for CrewAI content phase.
Generates high-quality images using configurable models via Replicate API.
Downloads, converts to JPEG, and stores permanently in S3.
Tracks cost via audit tracker using configured per-image cost.

Supports multiple Replicate models:
- google/imagen-3-fast: $0.025/image (fast, high-quality, recommended)
- google/imagen-3-generate: $0.030/image (premium quality)
- stability-ai/sdxl: $0.0023/image (budget-friendly)
- black-forest-labs/flux-dev: $0.025/image (balanced)
- black-forest-labs/flux-pro: $0.055/image (maximum quality)

Configure via environment variables:
- IMAGE_MODEL: Model identifier (e.g., "google/imagen-3-fast")
- IMAGE_COST_PER_GENERATION: Cost per image in USD
- REPLICATE_API_KEY: Your Replicate API key

See docs/IMAGE_PROVIDER_GUIDE.md for full model comparison and switching guide.
"""

from __future__ import annotations
from typing import Optional, Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import os
import logging

logger = logging.getLogger(__name__)


class ReplicateImageInput(BaseModel):
    prompt: str = Field(
        ...,
        description="Descriptive prompt of the image content (no disallowed content)",
    )
    size: str = Field(
        "1024x1024", description="Image size: 512x512, 768x768, 1024x1024"
    )
    aspect: str = Field(
        "square", description="Aspect ratio hint: square|landscape|portrait"
    )
    blog_id: Optional[str] = Field(
        None, description="Blog ID for S3 file naming (optional)"
    )


class ReplicateImageTool(BaseTool):
    name: str = "replicate_image_generate"
    description: str = (
        "Generate a single high-quality photorealistic image using Replicate AI models. "
        "Creates professional, stylish images directly relevant to the blog content. "
        "Input should describe the specific subject, context, and visual style needed. "
        "Produces photorealistic, modern aesthetic images with premium quality. "
        "Avoid brand logos, text overlays, or generic concepts. Returns a Markdown image tag. "
        "Currently configured model: Check IMAGE_MODEL environment variable."
    )
    args_schema: Type[BaseModel] = ReplicateImageInput

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, cost_per_image: Optional[float] = None, audit_tracker=None, **kwargs):
        """Initialize Replicate image tool with configurable model and cost tracking.
        
        Args:
            api_key: Replicate API key (defaults to REPLICATE_API_KEY env var)
            model: Model identifier (defaults to IMAGE_MODEL env var or google/imagen-3-fast)
            cost_per_image: Cost per image in USD (defaults to IMAGE_COST_PER_GENERATION env var or 0.025)
            audit_tracker: Audit tracker instance for cost tracking
        """
        super().__init__(**kwargs)
        self._api_key = api_key or os.getenv("REPLICATE_API_KEY")
        self._model = model or os.getenv("IMAGE_MODEL", "google/imagen-3-fast")
        self._cost_per_image = cost_per_image or float(os.getenv("IMAGE_COST_PER_GENERATION", "0.025"))
        self._audit_tracker = audit_tracker
        
        logger.info(f"🎨 ReplicateImageTool initialized with model: {self._model}, cost: ${self._cost_per_image}/image")
        
        try:
            import replicate  # noqa
            self._replicate_available = True
        except ImportError:
            self._replicate_available = False
            logger.warning(
                "Replicate library not installed; image tool will return placeholder."
            )

    def _run(self, prompt: str, size: str = "1024x1024", aspect: str = "square", blog_id: Optional[str] = None) -> str:  # type: ignore
        safe_prompt = prompt.strip()[:900]
        if not self._api_key or not self._replicate_available:
            return self._placeholder(safe_prompt)

        # Normalize size to match aspect ratio
        size_map = {
            "square": "1024x1024",
            "landscape": "1536x1024",  
            "portrait": "1024x1536"
        }
        
        # Use aspect hint to determine size
        if aspect in size_map:
            final_size = size_map[aspect]
        else:
            # Fallback to provided size or default
            final_size = size if size in size_map.values() else "1024x1024"

        # Add style & safety modifiers for photorealistic, stylish images
        final_prompt = (
            f"{safe_prompt}. Photorealistic photography style, professional lighting, high resolution, sharp focus, "
            f"modern aesthetic, visually striking composition, no text overlays, no logos, no watermarks. "
            f"Premium quality suitable for high-end blog content. Style: professional magazine photography."
        )

        try:
            import replicate

            # Set API token
            os.environ["REPLICATE_API_TOKEN"] = self._api_key

            # Parse width and height from size
            width, height = map(int, final_size.split('x'))

            # Run Imagen-3-Fast prediction
            logger.info(f"Generating image with Replicate model: {self._model}")
            output = replicate.run(
                self._model,
                input={
                    "prompt": final_prompt,
                    "aspect_ratio": f"{width}:{height}",
                    "output_format": "jpg",
                    "output_quality": 90,
                    "number_of_images": 1
                }
            )

            # Extract image URL from output
            # Imagen-3-Fast returns a list of FileOutput objects
            if not output:
                logger.warning("No image returned from Replicate")
                return self._placeholder(safe_prompt)

            # Convert to list if needed and get the first image URL
            output_list = list(output) if hasattr(output, '__iter__') else [output]
            if len(output_list) == 0:
                logger.warning("Empty output from Replicate")
                return self._placeholder(safe_prompt)

            temp_url = str(output_list[0])
            
            if not temp_url or not temp_url.startswith('http'):
                logger.warning(f"Invalid image URL from Replicate: {temp_url}")
                return self._placeholder(safe_prompt)

            # Store image permanently in S3
            try:
                from core.s3_storage import get_s3_storage

                s3_storage = get_s3_storage()

                # Use blog_id or generate unique ID for file naming
                file_id = blog_id if blog_id else f"temp-{hash(safe_prompt) % 10000}"
                permanent_url = s3_storage.store_hero_image(temp_url, file_id)

                alt = safe_prompt[:120]
                markdown = f'![{alt}]({permanent_url} "{alt}")'
                logger.info(f"Image stored permanently in S3: {permanent_url}")

            except Exception as e:
                logger.error(f"Failed to store image in S3: {e}")
                # Fallback to temporary URL if S3 fails
                alt = safe_prompt[:120]
                markdown = f'![{alt}]({temp_url} "{alt}")'

            # Track cost using configured per-image cost
            try:
                if self._audit_tracker and hasattr(
                    self._audit_tracker, "track_api_call"
                ):
                    self._audit_tracker.track_api_call(
                        model=self._model,  # Uses configured model (e.g., "google/imagen-3-fast")
                        input_tokens=len(final_prompt.split()),  # Approximate token count
                        output_tokens=1,  # One image generated
                        cost=self._cost_per_image,  # Uses configured cost (e.g., 0.025)
                        phase="image_generation",
                        agent_role="replicate_image_tool",
                    )
                    logger.info(f"💰 Tracked {self._model} image cost: ${self._cost_per_image}")
            except Exception as e:
                logger.debug(f"Image cost tracking failed: {e}", exc_info=True)

            return markdown

        except Exception as e:
            logger.warning(f"Replicate image generation failed: {e}", exc_info=True)
            return self._placeholder(safe_prompt)

    def _placeholder(self, prompt: str) -> str:
        return f"![Illustration placeholder for {prompt[:60]}](https://placehold.co/1024x1024?text=Image)"


__all__ = ["ReplicateImageTool"]
