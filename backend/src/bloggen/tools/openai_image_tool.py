"""OpenAI Image Generation Tool for CrewAI content phase.
Generates an illustrative image based on a blog section or title.
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

class OpenAIImageTool(BaseTool):
    name: str = "openai_image_generate"
    description: str = (
        "Generate a single high-quality illustrative image using OpenAI. Use for hero/section images. "
        "Input should describe visual scene, style (e.g., clean vector, photorealistic), and key subject. "
        "Avoid brand logos, faces, or sensitive content. Returns a Markdown image tag." )
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

    def _run(self, prompt: str, size: str = "1024x1024", aspect: str = "square") -> str:  # type: ignore
        safe_prompt = prompt.strip()[:900]
        if not self._api_key or not self._openai_available:
            return self._placeholder(safe_prompt)
        # Normalize size
        # Restrict to supported OpenAI sizes
        allowed_sizes = {"256x256","512x512","1024x1024","1536x1024","1024x1536","1792x1024","1024x1792"}
        if size not in allowed_sizes:
            size = "1024x1024"
        # Add style & safety modifiers
        final_prompt = (
            f"{safe_prompt}. Professional, cohesive blog illustration, high clarity, no text, no logos, no watermarks." )
        try:
            import openai
            client = openai.OpenAI(api_key=self._api_key)  # type: ignore[attr-defined]
            resp = client.images.generate(
                model="gpt-image-1",  # current unified image model
                prompt=final_prompt,
                size="1024x1024",  # keep fixed to satisfy typing & consistency
                n=1,
                response_format="url",
            )
            url = resp.data[0].url if resp and resp.data else None
            if not url:
                return self._placeholder(safe_prompt)
            alt = safe_prompt[:120]
            markdown = f"![{alt}]({url} \"{alt}\")"
            # Track cost (approx per image). Adjust if pricing changes.
            try:
                if self._audit_tracker and hasattr(self._audit_tracker, 'track_api_call'):
                    # Deduplicate cost logging per session/model
                    flag_name = '_logged_image_models'
                    logged = getattr(self._audit_tracker, flag_name, set())
                    if 'openai_image' not in logged:
                        try:
                            image_cost = float(os.getenv('OPENAI_IMAGE_FLAT_COST', '0.04'))
                        except ValueError:
                            image_cost = 0.04
                        self._audit_tracker.track_api_call(
                            model='openai_image',
                            input_tokens=0,
                            output_tokens=0,
                            cost=image_cost,
                            phase='image_generation',
                            agent_role='image_tool'
                        )
                        logged.add('openai_image')
                        setattr(self._audit_tracker, flag_name, logged)
            except Exception:
                logger.debug("Image cost tracking failed", exc_info=True)
            return markdown
        except Exception as e:
            logger.warning(f"OpenAI image generation failed: {e}")
            return self._placeholder(safe_prompt)

    def _placeholder(self, prompt: str) -> str:
        return f"![Illustration placeholder for {prompt[:60]}](https://placehold.co/1024x1024?text=Image)"

__all__ = ["OpenAIImageTool"]
