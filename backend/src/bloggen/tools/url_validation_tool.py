"""
URL Validation Tool for Fact Checking

This tool validates that URLs are accessible and working before including them in blog content.
It helps prevent link hallucination by requiring actual URL verification.
"""

import requests
import json
import time
import logging
from typing import Any, Optional, Type, List
from urllib.parse import urlparse
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class URLValidationInput(BaseModel):
    """Input schema for URL validation tool"""

    url: str = Field(..., description="The URL to validate")
    timeout: int = Field(default=10, description="Request timeout in seconds")


class URLValidationTool(BaseTool):
    """Tool to validate URLs and check their accessibility."""

    name: str = "url_validator"
    description: str = (
        "Validates URLs to check if they are accessible and return valid HTTP responses"
    )
    args_schema: Type[BaseModel] = URLValidationInput
    audit_tracker: Optional[Any] = None

    def __init__(self, audit_tracker=None, **kwargs):
        """Initialize the URL validation tool."""
        super().__init__(**kwargs)
        self.audit_tracker = audit_tracker

    def _run(self, url: str, timeout: int = 10) -> str:
        """
        Validate a URL and return its accessibility status.

        Args:
            url: The URL to validate
            timeout: Request timeout in seconds

        Returns:
            JSON string with validation results
        """
        try:
            # Track the API call for audit purposes
            if self.audit_tracker:
                try:
                    self.audit_tracker.track_api_call(
                        model="url_validation",
                        input_tokens=0,
                        output_tokens=0,
                        cost=0.0,  # Free operation
                        phase="fact_checking",
                        agent_role="url_validator",
                    )
                except Exception:
                    logger.debug("URL validation cost tracking failed", exc_info=True)

            # Parse URL to ensure it's valid
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return self._format_result(
                    url=url,
                    accessible=False,
                    status_code=None,
                    error="Invalid URL format - missing scheme or domain",
                    final_url=None,
                    response_time=None,
                )

            # Validate the URL with proper headers
            start_time = time.time()
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; BlogGenFactChecker/1.0; +https://bloggen.ai/bot)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }

            response = requests.get(
                url,
                timeout=timeout,
                headers=headers,
                allow_redirects=True,
                verify=True,  # Verify SSL certificates
            )

            response_time = time.time() - start_time

            # Check for successful response
            is_accessible = 200 <= response.status_code < 400

            return self._format_result(
                url=url,
                accessible=is_accessible,
                status_code=response.status_code,
                error=None if is_accessible else f"HTTP {response.status_code}",
                final_url=response.url if response.url != url else None,
                response_time=response_time,
            )

        except requests.exceptions.Timeout:
            return self._format_result(
                url=url,
                accessible=False,
                status_code=None,
                error="Request timeout - URL took too long to respond",
                final_url=None,
                response_time=timeout,
            )

        except requests.exceptions.SSLError:
            return self._format_result(
                url=url,
                accessible=False,
                status_code=None,
                error="SSL certificate error - invalid or expired certificate",
                final_url=None,
                response_time=None,
            )

        except requests.exceptions.ConnectionError:
            return self._format_result(
                url=url,
                accessible=False,
                status_code=None,
                error="Connection failed - domain may not exist or be unreachable",
                final_url=None,
                response_time=None,
            )

        except requests.exceptions.RequestException as e:
            return self._format_result(
                url=url,
                accessible=False,
                status_code=None,
                error=f"Request failed: {str(e)}",
                final_url=None,
                response_time=None,
            )

        except Exception as e:
            logger.error(f"Unexpected error validating URL {url}: {e}")
            return self._format_result(
                url=url,
                accessible=False,
                status_code=None,
                error=f"Validation error: {str(e)}",
                final_url=None,
                response_time=None,
            )

    def _format_result(
        self,
        url: str,
        accessible: bool,
        status_code: Optional[int],
        error: Optional[str],
        final_url: Optional[str],
        response_time: Optional[float],
    ) -> str:
        """Format validation result as JSON string for the agent"""
        import json

        result = {
            "url": url,
            "accessible": accessible,
            "status_code": status_code,
            "error": error,
            "final_url": final_url,
            "response_time": round(response_time, 2) if response_time else None,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        }

        # Log the result for debugging
        status = "✅ ACCESSIBLE" if accessible else "❌ BROKEN"
        logger.info(f"URL Validation: {status} - {url} (Status: {status_code})")

        return json.dumps(result, indent=2)


class BulkURLValidationInput(BaseModel):
    """Input schema for bulk URL validation"""

    urls: List[str] = Field(..., description="List of URLs to validate")
    timeout: int = Field(default=10, description="Request timeout in seconds per URL")


class BulkURLValidationTool(BaseTool):
    """Tool to validate multiple URLs at once."""

    name: str = "bulk_url_validator"
    description: str = (
        "Validates multiple URLs at once to check accessibility and return validation status for each"
    )
    args_schema: Type[BaseModel] = BulkURLValidationInput
    audit_tracker: Optional[Any] = None

    def __init__(self, audit_tracker=None, **kwargs):
        """Initialize the bulk URL validation tool."""
        super().__init__(**kwargs)
        self.audit_tracker = audit_tracker

    def _run(self, urls: List[str], timeout: int = 10) -> str:
        """Validate multiple URLs and return a comprehensive report."""
        results = []
        total_urls = len(urls)
        accessible_count = 0

        logger.info(f"Starting bulk URL validation for {total_urls} URLs")

        for i, url in enumerate(urls, 1):
            logger.info(f"Validating URL {i}/{total_urls}: {url}")

            try:
                # Track audit if available
                if self.audit_tracker and hasattr(self.audit_tracker, "track_api_call"):
                    try:
                        self.audit_tracker.track_api_call(
                            model="url_validation",
                            input_tokens=1,
                            output_tokens=1,
                            cost=0.0001,
                            phase="fact_checking",
                            agent_role="url_validator",
                        )
                    except Exception:
                        logger.debug(
                            "URL validation cost tracking failed", exc_info=True
                        )

                # Use requests to validate URL
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }

                response = requests.get(
                    url, timeout=timeout, headers=headers, allow_redirects=True
                )
                status_code = response.status_code
                accessible = 200 <= status_code < 400

                if accessible:
                    accessible_count += 1

                result = {
                    "url": url,
                    "status_code": status_code,
                    "accessible": accessible,
                    "response_time_ms": int(response.elapsed.total_seconds() * 1000),
                    "final_url": response.url if response.url != url else None,
                    "error": None,
                }

            except requests.exceptions.SSLError as e:
                result = {
                    "url": url,
                    "status_code": None,
                    "accessible": False,
                    "response_time_ms": None,
                    "final_url": None,
                    "error": f"SSL Error: {str(e)}",
                }
                logger.warning(f"SSL error for {url}: {e}")

            except requests.exceptions.ConnectionError as e:
                result = {
                    "url": url,
                    "status_code": None,
                    "accessible": False,
                    "response_time_ms": None,
                    "final_url": None,
                    "error": f"Connection Error: {str(e)}",
                }
                logger.warning(f"Connection error for {url}: {e}")

            except requests.exceptions.Timeout as e:
                result = {
                    "url": url,
                    "status_code": None,
                    "accessible": False,
                    "response_time_ms": None,
                    "final_url": None,
                    "error": f"Timeout Error: {str(e)}",
                }
                logger.warning(f"Timeout for {url}: {e}")

            except Exception as e:
                result = {
                    "url": url,
                    "status_code": None,
                    "accessible": False,
                    "response_time_ms": None,
                    "final_url": None,
                    "error": f"Unknown Error: {str(e)}",
                }
                logger.error(f"Unexpected error for {url}: {e}")

            results.append(result)

        # Generate summary
        broken_urls = [r for r in results if not r["accessible"]]
        success_rate = (accessible_count / total_urls) * 100 if total_urls > 0 else 0

        summary = {
            "total_urls": total_urls,
            "accessible_urls": accessible_count,
            "broken_urls": len(broken_urls),
            "success_rate_percent": round(success_rate, 1),
            "validation_results": results,
        }

        logger.info(
            f"Bulk URL validation complete: {accessible_count}/{total_urls} URLs accessible ({success_rate:.1f}%)"
        )

        return json.dumps(summary, indent=2)
