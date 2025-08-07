"""
Tools Manager for Blog Generation

Manages and provides tools for different phases of blog generation.
Follows Single Responsibility Principle - only manages tool creation and access.
"""

from typing import List, Any
import logging

logger = logging.getLogger(__name__)


class ToolsManager:
    """Manages tools for different phases of blog generation."""
    
    def __init__(self):
        self._research_tools = None
        self._content_tools = None
    
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
        
        # Try to load external research tools from crewai_tools
        try:
            from crewai_tools import SerperDevTool, ScrapeWebsiteTool
            tools.extend([SerperDevTool(), ScrapeWebsiteTool()])
            logger.debug("✅ External research tools loaded")
        except ImportError as e:
            logger.warning(f"External research tools not available: {e}")
        except Exception as e:
            logger.error(f"Error loading external research tools: {e}")
        
        # Fallback: If no external tools available, return empty list
        # The system will still work, just without web research capabilities
        logger.info(f"Loaded {len(tools)} research tools")
        return tools
    
    def _load_content_tools(self) -> List[Any]:
        """Load content generation tools with proper error handling."""
        tools = []
        
        try:
            from bloggen.tools import UnsplashImageTool
            tools.append(UnsplashImageTool())
            logger.debug("✅ UnsplashImageTool loaded")
        except ImportError as e:
            logger.warning(f"UnsplashImageTool not available: {e}")
        except Exception as e:
            logger.error(f"Error loading UnsplashImageTool: {e}")
        
        # Add other content tools here as needed
        logger.info(f"Loaded {len(tools)} content tools")
        return tools
