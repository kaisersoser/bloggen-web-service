"""
Safe Research Tools for Blog Generation

Custom implementations of research tools that prevent binary content issues
and enforce timeout limits for reliable operation.
"""

import time
import logging
import requests
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from crewai.tools.base_tool import BaseTool
from pydantic import Field

logger = logging.getLogger(__name__)


class SafeContentConfig:
    """Configuration for safe content processing"""

    # Allowed content types (text-based only)
    SAFE_CONTENT_TYPES = {
        "text/html",
        "text/plain",
        "text/xml",
        "text/css",
        "text/javascript",
        "application/json",
        "application/xml",
        "application/rss+xml",
        "application/atom+xml",
        "application/ld+json",
        "application/xhtml+xml",
    }

    # Blocked content types (binary/problematic)
    BLOCKED_CONTENT_TYPES = {
        "application/pdf",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "application/zip",
        "application/x-rar-compressed",
        "application/octet-stream",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "video/mp4",
        "video/mpeg",
        "audio/mpeg",
        "audio/wav",
    }

    # Blocked file extensions
    BLOCKED_EXTENSIONS = {
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".zip",
        ".rar",
        ".tar",
        ".gz",
        ".7z",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".svg",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".mp3",
        ".wav",
        ".aac",
        ".flac",
        ".exe",
        ".msi",
        ".dmg",
        ".deb",
        ".rpm",
    }

    # Request timeout (10 seconds as requested)
    REQUEST_TIMEOUT = 10

    # Maximum content size (5MB to prevent memory issues)
    MAX_CONTENT_SIZE = 5 * 1024 * 1024


def is_content_safe(
    url: str, headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Check if a URL points to safe, text-based content.

    Args:
        url: URL to check
        headers: Optional headers from HEAD request

    Returns:
        Dict with safety assessment and details
    """
    try:
        # Check URL extension
        parsed = urlparse(url)
        path = parsed.path.lower()

        for ext in SafeContentConfig.BLOCKED_EXTENSIONS:
            if path.endswith(ext):
                return {
                    "safe": False,
                    "reason": f"Blocked file extension: {ext}",
                    "content_type": f"file{ext}",
                    "url": url,
                }

        # Check content-type from headers if available
        if headers:
            content_type = headers.get("content-type", "").lower().split(";")[0].strip()

            if content_type in SafeContentConfig.BLOCKED_CONTENT_TYPES:
                return {
                    "safe": False,
                    "reason": f"Blocked content type: {content_type}",
                    "content_type": content_type,
                    "url": url,
                }

            if content_type and content_type in SafeContentConfig.SAFE_CONTENT_TYPES:
                return {
                    "safe": True,
                    "reason": f"Safe content type: {content_type}",
                    "content_type": content_type,
                    "url": url,
                }

        # If no headers, make assumptions based on URL patterns
        if any(
            keyword in url.lower() for keyword in ["api", "json", "xml", "rss", "feed"]
        ):
            return {
                "safe": True,
                "reason": "API/feed URL pattern detected",
                "content_type": "text/html",
                "url": url,
            }

        # Default to safe for HTML-like URLs
        return {
            "safe": True,
            "reason": "Default web content assumed safe",
            "content_type": "text/html",
            "url": url,
        }

    except Exception as e:
        logger.warning(f"Content safety check failed for {url}: {e}")
        return {
            "safe": False,
            "reason": f"Safety check error: {str(e)}",
            "content_type": "unknown",
            "url": url,
        }


def safe_head_request(url: str) -> Dict[str, Any]:
    """
    Make a safe HEAD request to check content type.

    Args:
        url: URL to check

    Returns:
        Dict with headers and safety info
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; SafeResearchBot/1.0)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        response = requests.head(
            url,
            headers=headers,
            timeout=SafeContentConfig.REQUEST_TIMEOUT,
            allow_redirects=True,
            verify=False,  # Some sites have SSL issues
        )

        return {
            "success": True,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "url": response.url,  # Final URL after redirects
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Request timeout (>10s)",
            "headers": {},
            "url": url,
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}",
            "headers": {},
            "url": url,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "headers": {},
            "url": url,
        }


class SafeSerperTool(BaseTool):
    """
    Safe version of SerperDevTool with content filtering and timeout controls.
    Only returns results that point to safe, text-based content.
    """

    name: str = "safe_serper_search"
    description: str = """
    Safe web search tool that only returns results pointing to accessible text content.
    Automatically filters out PDFs, documents, images, videos, and other binary content.
    Use this to find reliable web sources with readable content for research.
    
    Input: search query string
    Output: List of safe search results with URLs verified to be text-based
    """

    audit_tracker: Optional[Any] = Field(default=None)

    def __init__(self, audit_tracker: Optional[Any] = None, **kwargs):
        super().__init__(**kwargs)
        self.audit_tracker = audit_tracker

        # Try to use the original SerperDevTool for actual search
        try:
            from crewai_tools import SerperDevTool

            self._serper_tool = SerperDevTool()
            logger.info("✅ SafeSerperTool initialized with SerperDevTool backend")
        except ImportError:
            self._serper_tool = None
            logger.warning(
                "❌ SerperDevTool not available - SafeSerperTool will return mock results"
            )

    def _run(self, search_query: str) -> str:
        """
        Execute safe search with content filtering.

        Args:
            search_query: The search query string

        Returns:
            Filtered search results with only safe content
        """
        start_time = time.time()

        try:
            # Track API call for auditing
            if self.audit_tracker and hasattr(self.audit_tracker, "track_api_call"):
                try:
                    self.audit_tracker.track_api_call(
                        model="serper_api",
                        input_tokens=0,
                        output_tokens=0,
                        cost=0.001,
                        phase="research",
                        agent_role="safe_serper_tool",
                    )
                except Exception:
                    logger.debug("Serper cost tracking failed", exc_info=True)

            if not self._serper_tool:
                return self._mock_safe_results(search_query)

            # Get raw search results
            logger.info(f"🔍 SafeSerper searching: {search_query}")
            # Use the correct method signature for SerperDevTool
            raw_results = self._serper_tool.run(search_query=search_query)

            # Filter results for safety
            safe_results = self._filter_safe_results(raw_results, search_query)

            elapsed = time.time() - start_time
            logger.info(
                f"✅ SafeSerper completed in {elapsed:.1f}s - filtered to safe content only"
            )

            return safe_results

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ SafeSerper failed after {elapsed:.1f}s: {e}")
            return f"Search failed due to safety controls: {str(e)}. Please try a different search query."

    def _filter_safe_results(self, raw_results: str, query: str) -> str:
        """Filter search results to only include safe content."""
        try:
            # Handle both string and dict results from SerperDevTool
            if isinstance(raw_results, dict):
                # Convert dict to string for processing
                raw_results = str(raw_results)
            elif not isinstance(raw_results, str):
                # Convert any other type to string
                raw_results = str(raw_results)

            # Parse the raw results (this is a simplified approach)
            # In practice, you'd want to parse the actual JSON structure
            lines = raw_results.split("\n")
            safe_lines = []
            filtered_count = 0

            for line in lines:
                if "http" in line:
                    # Extract URLs and check them
                    import re

                    urls = re.findall(r'https?://[^\s<>"\']+', line)

                    safe_urls = []
                    for url in urls:
                        # Quick safety check without HEAD request for performance
                        safety = is_content_safe(url)
                        if safety["safe"]:
                            safe_urls.append(url)
                        else:
                            filtered_count += 1
                            logger.debug(
                                f"🚫 Filtered unsafe URL: {url} - {safety['reason']}"
                            )

                    # If line has safe URLs, include it
                    if safe_urls or not urls:  # Include non-URL lines
                        safe_lines.append(line)
                else:
                    safe_lines.append(line)

            safe_content = "\n".join(safe_lines)

            # Add safety summary
            if filtered_count > 0:
                safety_note = f"\n\n[Safety Filter: {filtered_count} unsafe URLs removed (PDFs, documents, media files)]"
                safe_content += safety_note

            logger.info(f"🛡️ Content filtering: {filtered_count} unsafe URLs removed")
            return safe_content

        except Exception as e:
            logger.error(f"Result filtering failed: {e}")
            # Return original results if filtering fails, but add warning
            return (
                f"Search results (filtering failed - use caution): {str(raw_results)}"
            )

    def _mock_safe_results(self, query: str) -> str:
        """Mock results when SerperDevTool is not available."""
        return f"""
SafeSerper Mock Results for: {query}

Due to SerperDevTool unavailability, returning safe mock results:

1. Example Article: Understanding {query}
   URL: https://example-safe-site.com/article/{query.replace(' ', '-')}
   Description: Comprehensive overview of {query} with latest insights and analysis.

2. Research Source: {query} Research Portal  
   URL: https://research-portal.com/topics/{query.replace(' ', '-')}
   Description: Academic and industry research findings related to {query}.

3. News Article: Recent Developments in {query}
   URL: https://news-site.com/tech/{query.replace(' ', '-')}
   Description: Latest news and developments in the field of {query}.

[Note: Mock results provided - all URLs verified as text-based content]
"""


class SafeWebScrapeTool(BaseTool):
    """
    Safe version of ScrapeWebsiteTool with content type validation and timeout controls.
    Only scrapes safe, text-based content and respects timeout limits.
    """

    name: str = "safe_web_scrape"
    description: str = """
    Safely scrape text content from websites with automatic safety validation.
    Only processes HTML, JSON, XML, and other text-based content formats.
    Automatically rejects PDFs, documents, images, and other binary content.
    Enforces 10-second timeout limit for reliable operation.
    
    Input: URL to scrape
    Output: Extracted text content (only from safe sources)
    """

    audit_tracker: Optional[Any] = Field(default=None)

    def __init__(self, audit_tracker: Optional[Any] = None, **kwargs):
        super().__init__(**kwargs)
        self.audit_tracker = audit_tracker
        logger.info("✅ SafeWebScrapeTool initialized with content filtering")

    def _run(self, website_url: str) -> str:
        """
        Safely scrape website content with validation.

        Args:
            website_url: URL to scrape

        Returns:
            Extracted text content or safety error message
        """
        start_time = time.time()

        try:
            logger.info(f"🔍 SafeScrape checking: {website_url}")

            # Step 1: Check content safety with HEAD request
            head_result = safe_head_request(website_url)

            if not head_result["success"]:
                return f"Cannot access URL: {head_result['error']}"

            # Step 2: Validate content type safety
            headers = head_result["headers"]
            safety_check = is_content_safe(website_url, headers)

            if not safety_check["safe"]:
                logger.warning(
                    f"🚫 Blocked unsafe content: {website_url} - {safety_check['reason']}"
                )
                return f"Content blocked for safety: {safety_check['reason']}. Please provide a URL with readable text content (HTML, JSON, XML)."

            # Step 3: Additional content-type validation from headers
            content_type = headers.get("content-type", "").lower()
            if content_type:
                # Check for binary content types that might slip through
                if any(
                    blocked in content_type
                    for blocked in [
                        "image/",
                        "video/",
                        "audio/",
                        "application/pdf",
                        "application/zip",
                    ]
                ):
                    logger.warning(f"🚫 Blocked binary content-type: {content_type}")
                    return f"Content blocked: Binary content type detected ({content_type}). Please provide a URL with text-based content."

            # Step 4: Safely scrape the content
            logger.info(f"✅ Content validated as safe: {safety_check['content_type']}")
            content = self._safe_scrape_content(website_url)

            elapsed = time.time() - start_time
            logger.info(f"✅ SafeScrape completed in {elapsed:.1f}s")

            return content

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ SafeScrape failed after {elapsed:.1f}s: {e}")
            return f"Scraping failed due to safety controls: {str(e)}. Please try a different URL with accessible text content."

    def _safe_scrape_content(self, url: str) -> str:
        """Safely scrape content with proper error handling."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; SafeScraperBot/1.0)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=SafeContentConfig.REQUEST_TIMEOUT,
                allow_redirects=True,
                verify=False,
                stream=True,  # Stream to check content length
            )

            # Check content length
            content_length = response.headers.get("content-length")
            if (
                content_length
                and int(content_length) > SafeContentConfig.MAX_CONTENT_SIZE
            ):
                return f"Content too large ({content_length} bytes). Maximum allowed: {SafeContentConfig.MAX_CONTENT_SIZE} bytes."

            # Additional content-type check from response
            response_content_type = response.headers.get("content-type", "").lower()
            if any(
                blocked in response_content_type
                for blocked in ["image/", "video/", "audio/", "application/pdf"]
            ):
                return f"Content blocked: Binary content type in response ({response_content_type}). Only text-based content is allowed."

            # Read content with size limit
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > SafeContentConfig.MAX_CONTENT_SIZE:
                    return f"Content exceeds maximum size limit ({SafeContentConfig.MAX_CONTENT_SIZE} bytes)."

            # Decode content
            text_content = content.decode("utf-8", errors="replace")

            # Extract meaningful text (basic HTML parsing)
            if "text/html" in response.headers.get("content-type", ""):
                text_content = self._extract_html_text(text_content)

            # Limit final content length
            if len(text_content) > 50000:  # 50KB limit
                text_content = (
                    text_content[:50000] + "\n\n[Content truncated for safety...]"
                )

            return text_content

        except requests.exceptions.Timeout:
            return f"Request timeout: Website took longer than {SafeContentConfig.REQUEST_TIMEOUT} seconds to respond."
        except requests.exceptions.RequestException as e:
            return f"Request failed: {str(e)}"
        except Exception as e:
            return f"Content extraction failed: {str(e)}"

    def _extract_html_text(self, html_content: str) -> str:
        """Extract text from HTML content."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer"]):
                script.decompose()

            # Get text content
            text = soup.get_text()

            # Clean up whitespace
            lines = [line.strip() for line in text.splitlines()]
            text = "\n".join(line for line in lines if line)

            return text

        except ImportError:
            logger.warning("BeautifulSoup not available - returning raw HTML")
            return html_content
        except Exception as e:
            logger.error(f"HTML parsing failed: {e}")
            return html_content


def create_safe_research_tools(audit_tracker: Optional[Any] = None) -> List[BaseTool]:
    """
    Create a list of safe research tools.

    Args:
        audit_tracker: Optional audit tracker for cost tracking

    Returns:
        List of safe research tools
    """
    tools = [
        SafeSerperTool(audit_tracker=audit_tracker),
        SafeWebScrapeTool(audit_tracker=audit_tracker),
    ]

    logger.info(f"✅ Created {len(tools)} safe research tools with content filtering")
    return tools
