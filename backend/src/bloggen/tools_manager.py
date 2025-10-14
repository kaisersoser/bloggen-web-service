"""
Tools Manager for Blog Generation

Manages and provides tools for different phases of blog generation.
Follows Single Responsibility Principle - only manages tool creation and access.
"""

from typing import List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ToolsManager:
    """Manages tools for different phases of blog generation."""

    def __init__(self, audit_tracker: Optional[Any] = None):
        self._research_tools = None
        self._content_tools = None
        self.audit_tracker = audit_tracker

    def get_research_tools(self) -> List[Any]:
        """Get tools for research phase."""
        if self._research_tools is None:
            self._research_tools = self._load_research_tools()
        return self._research_tools

    def get_content_tools(self) -> List[Any]:
        """Get tools for content generation phase."""
        if self._content_tools is None:
            self._content_tools = self._load_content_tools()
        return self._content_tools

    def _load_research_tools(self) -> List[Any]:
        """Load research tools with proper error handling."""
        tools = []

        # Add URL validation tools for fact checking
        try:
            from bloggen.tools import URLValidationTool, BulkURLValidationTool

            url_tool = URLValidationTool(audit_tracker=self.audit_tracker)
            bulk_url_tool = BulkURLValidationTool(audit_tracker=self.audit_tracker)
            tools.extend([url_tool, bulk_url_tool])
            logger.debug("✅ URL validation tools loaded")
        except ImportError as e:
            logger.warning(f"URL validation tools not available: {e}")
        except Exception as e:
            logger.error(f"Error loading URL validation tools: {e}")

        # Use safe research tools instead of standard ones to prevent binary content issues
        try:
            from bloggen.tools import create_safe_research_tools

            safe_tools = create_safe_research_tools(audit_tracker=self.audit_tracker)
            tools.extend(safe_tools)
            logger.info(
                "✅ Safe research tools loaded (content filtering + 10s timeout)"
            )

        except ImportError as e:
            logger.warning(f"Safe research tools not available: {e}")
            # Fallback to standard tools with warning
            try:
                from crewai_tools import SerperDevTool, ScrapeWebsiteTool

                logger.warning(
                    "⚠️ Using standard research tools - binary content may cause issues"
                )

                audit_tracker = self.audit_tracker

                if audit_tracker and hasattr(audit_tracker, "track_api_call"):
                    # Define an instrumented subclass so we don't mutate pydantic attributes
                    class InstrumentedSerperDevTool(SerperDevTool):  # type: ignore
                        def _run(
                            self, *args, **kwargs
                        ):  # override underlying execution hook
                            # Support positional first arg as search_query
                            if args and "search_query" not in kwargs:
                                kwargs["search_query"] = args[0]
                            result = super()._run(**kwargs)
                            try:
                                audit_tracker.track_api_call(
                                    model="serper_api",
                                    input_tokens=0,
                                    output_tokens=0,
                                    cost=0.001,
                                    phase="research",
                                    agent_role="serper_tool",
                                )
                            except Exception:
                                logger.debug(
                                    "Serper cost tracking failed", exc_info=True
                                )
                            return result

                    serper_tool = InstrumentedSerperDevTool()
                    logger.info(
                        "🧪 Using instrumented SerperDevTool subclass for cost tracking"
                    )
                else:
                    serper_tool = SerperDevTool()
                    logger.info(
                        "ℹ️ Using standard SerperDevTool (no audit tracker detected)"
                    )

                tools.extend([serper_tool, ScrapeWebsiteTool()])
                logger.debug("✅ Standard research tools loaded as fallback")
            except ImportError as e2:
                logger.warning(f"Standard research tools also not available: {e2}")
        except Exception as e:
            logger.error(f"Error loading safe research tools: {e}")

        # Fallback: If no external tools available, return empty list
        # The system will still work, just without web research capabilities
        logger.info(f"Loaded {len(tools)} research tools")
        return tools

    # --- Internal Helpers -------------------------------------------------
    def _instrument_serper_tool(
        self, tool: Any
    ) -> None:  # legacy no-op (kept for backward refs)
        return

    def _load_content_tools(self) -> List[Any]:
        """Load content generation tools with proper error handling and provider selection."""
        tools = []

        try:
            from core.config import config
            from bloggen.tools import UnsplashImageTool

            # Always include Unsplash tool as it's free
            tools.append(UnsplashImageTool(audit_tracker=self.audit_tracker))

            # Conditionally include AI image tool based on configuration
            if config.features.enable_ai_image_generation:
                # Determine which image provider to use (replicate or openai)
                image_provider = getattr(config.api, 'image_provider', 'replicate')
                image_model = getattr(config.api, 'image_model', 'google/imagen-3-fast')
                image_cost = getattr(config.api, 'image_cost_per_generation', 0.025)
                
                logger.info(f"🎨 Loading image provider: {image_provider} (model: {image_model}, cost: ${image_cost}/image)")
                
                if image_provider == 'replicate':
                    from bloggen.tools.replicate_image_tool import ReplicateImageTool
                    tools.append(ReplicateImageTool(
                        api_key=config.api.replicate_key,
                        model=image_model,
                        cost_per_image=image_cost,
                        audit_tracker=self.audit_tracker
                    ))
                    logger.debug(f"✅ UnsplashImageTool + ReplicateImageTool loaded ({image_model})")
                elif image_provider == 'openai':
                    from bloggen.tools.openai_image_tool import OpenAIImageTool
                    tools.append(OpenAIImageTool(audit_tracker=self.audit_tracker))
                    logger.debug(f"✅ UnsplashImageTool + OpenAIImageTool loaded ({image_model})")
                else:
                    logger.warning(f"⚠️ Unknown image provider '{image_provider}', defaulting to Replicate")
                    from bloggen.tools.replicate_image_tool import ReplicateImageTool
                    tools.append(ReplicateImageTool(
                        api_key=config.api.replicate_key,
                        model=image_model,
                        cost_per_image=image_cost,
                        audit_tracker=self.audit_tracker
                    ))
                    logger.debug(f"✅ UnsplashImageTool + ReplicateImageTool (default fallback)")
            else:
                logger.debug(
                    "✅ UnsplashImageTool loaded (AI image generation disabled)"
                )

        except ImportError as e:
            logger.warning(f"Image tools not available: {e}")
        except Exception as e:
            logger.error(f"Error loading image tools: {e}")

        # Add other content tools here as needed
        logger.info(f"Loaded {len(tools)} content tools")
        return tools
