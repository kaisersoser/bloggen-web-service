"""OpenAI Image Generation Tool for CrewAI content phase.
Generates an illustrative image based on a blog section or title.
Downloads, converts to JPEG, and stores permanently in S3.
Tracks cost via audit tracker using a flat per-image cost estimate (adjust if pricing changes).
"""
from __future__ import annotations
from typing import Optional, Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
import os
import logging

logger = logging.getLogger(__name__)

class OpenAIImageInput(BaseModel):
    prompt: str = Field(..., description="Descriptive prompt of the image content (no disallowed content)")
    size: str = Field("1024x1024", description="Image size: 512x512, 768x768, 1024x1024")
    aspect: str = Field("square", description="Aspect ratio hint: square|landscape|portrait")
    blog_id: Optional[str] = Field(None, description="Blog ID for S3 file naming (optional)")

class OpenAIImageTool(BaseTool):
    name: str = "openai_image_generate"
    description: str = (
        "Generate a single high-quality photorealistic image using OpenAI DALL-E 3. "
        "Creates professional, stylish images directly relevant to the blog content. "
        "Input should describe the specific subject, context, and visual style needed. "
        "Produces photorealistic, modern aesthetic images with premium quality. "
        "Avoid brand logos, text overlays, or generic concepts. Returns a Markdown image tag." )
    args_schema: Type[BaseModel] = OpenAIImageInput

    def __init__(self, api_key: Optional[str] = None, audit_tracker=None, **kwargs):
        super().__init__(**kwargs)
        self._api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._audit_tracker = audit_tracker
        try:
            import openai  # noqa
            self._openai_available = True
        except ImportError:
            self._openai_available = False
            logger.warning("OpenAI library not installed; image tool will return placeholder.")

    def _run(self, prompt: str, size: str = "1024x1024", aspect: str = "square", blog_id: Optional[str] = None) -> str:  # type: ignore
        safe_prompt = prompt.strip()[:900]
        if not self._api_key or not self._openai_available:
            return self._placeholder(safe_prompt)
        # Normalize size
        # Restrict to supported OpenAI sizes
        allowed_sizes = {"256x256","512x512","1024x1024","1536x1024","1024x1536","1792x1024","1024x1792"}
        if size not in allowed_sizes:
            size = "1024x1024"
        # Add style & safety modifiers for photorealistic, stylish images
        final_prompt = (
            f"{safe_prompt}. Photorealistic photography style, professional lighting, high resolution, sharp focus, "
            f"modern aesthetic, visually striking composition, no text overlays, no logos, no watermarks. "
            f"Premium quality suitable for high-end blog content. Style: professional magazine photography." )
        try:
            import openai
            client = openai.OpenAI(api_key=self._api_key)  # type: ignore[attr-defined]
            
            # Validate size parameter for DALL-E 3
            valid_sizes = ["1024x1024", "1024x1792", "1792x1024"]
            final_size = size if size in valid_sizes else "1024x1024"
            
            resp = client.images.generate(
                model="dall-e-3",  # Use latest DALL-E model for highest quality
                prompt=final_prompt,
                size=final_size,  # type: ignore[arg-type]
                quality="standard",  # Balance between quality and cost
                n=1,
                response_format="url",
            )
            temp_url = resp.data[0].url if resp and resp.data else None
            if not temp_url:
                return self._placeholder(safe_prompt)
            
            # Store image permanently in S3
            try:
                from core.s3_storage import get_s3_storage
                s3_storage = get_s3_storage()
                
                # Use blog_id or generate unique ID for file naming
                file_id = blog_id if blog_id else f"temp-{hash(safe_prompt) % 10000}"
                permanent_url = s3_storage.store_hero_image(temp_url, file_id)
                
                alt = safe_prompt[:120]
                markdown = f"![{alt}]({permanent_url} \"{alt}\")"
                logger.info(f"Image stored permanently in S3: {permanent_url}")
                
            except Exception as e:
                logger.error(f"Failed to store image in S3: {e}")
                # Fallback to temporary URL if S3 fails
                alt = safe_prompt[:120]
                markdown = f"![{alt}]({temp_url} \"{alt}\")"
            
            # Track cost (approx per image). Adjust if pricing changes.
            try:
                if self._audit_tracker and hasattr(self._audit_tracker, 'track_api_call'):
                    # Track each image generation individually
                    image_cost = float(os.getenv('OPENAI_IMAGE_FLAT_COST', '0.04'))
                    self._audit_tracker.track_api_call(
                        model='dall-e-3',
                        input_tokens=len(final_prompt.split()),  # Approximate token count
                        output_tokens=1,  # One image generated
                        cost=image_cost,
                        phase='image_generation',
                        agent_role='openai_image_tool'
                    )
            except Exception:
                logger.debug("Image cost tracking failed", exc_info=True)
            return markdown
        except Exception as e:
            logger.warning(f"OpenAI image generation failed: {e}")
            return self._placeholder(safe_prompt)

    def _placeholder(self, prompt: str) -> str:
        return f"![Illustration placeholder for {prompt[:60]}](https://placehold.co/1024x1024?text=Image)"

__all__ = ["OpenAIImageTool"]
