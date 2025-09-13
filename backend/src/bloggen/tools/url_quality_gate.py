"""
URL Quality Gate Tool - Automated URL validation and fixing before content finalization.

This tool provides automated protection against URL hallucination by scanning
final blog content for broken URLs and replacing them with working alternatives.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from urllib.parse import urlparse, urljoin
import requests
from dataclasses import dataclass
from .url_validation_tool import URLValidationTool


@dataclass
class URLAnalysis:
    """Analysis result for a single URL"""
    original_url: str
    is_working: bool
    status_code: Optional[int]
    error: Optional[str]
    replacement_url: Optional[str] = None
    action_taken: str = "none"  # "none", "replaced", "removed", "fixed"


@dataclass
class QualityGateReport:
    """Report of all URL quality gate actions"""
    total_urls_found: int
    working_urls: int
    broken_urls: int
    urls_replaced: int
    urls_removed: int
    urls_fixed: int
    analysis_results: List[URLAnalysis]
    content_modified: bool


class URLQualityGate:
    """
    Automated URL quality gate that scans and fixes broken URLs in blog content.
    
    This tool provides immediate protection against URL hallucination by:
    1. Extracting all URLs from blog content
    2. Validating each URL's accessibility  
    3. Attempting to fix broken URLs with alternatives
    4. Removing unfixable broken URLs
    5. Generating a quality report
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.url_validator = URLValidationTool()
        
        # Common domain alternatives for fixing broken URLs
        self.domain_alternatives = {
            'nationalgeographic.com': ['www.nationalgeographic.com', 'nationalgeographic.org'],
            'rei.com': ['www.rei.com', 'blog.rei.com'],
            'climbing.com': ['www.climbing.com', 'rockandice.com'],
            'outdoorlife.com': ['www.outdoorlife.com', 'fieldandstream.com'],
            'mountainproject.com': ['www.mountainproject.com'],
            'alpinist.com': ['www.alpinist.com', 'alpinist.org'],
            'turismoroma.it': ['www.turismoroma.it', 'www.roma.it'],
            'parisinfo.com': ['www.parisinfo.com', 'en.parisinfo.com'],
            'indonesia.travel': ['www.indonesia.travel', 'wonderfulindonesia.id'],
            'barcelonaturisme.com': ['www.barcelonaturisme.com', 'www.visitbarcelona.com']
        }
        
        # Fallback placeholder URLs for when we can't find alternatives
        self.placeholder_urls = {
            'travel': 'https://www.example.com/travel-destination',
            'climbing': 'https://www.example.com/climbing-guide',
            'outdoor': 'https://www.example.com/outdoor-activities',
            'tourism': 'https://www.example.com/tourist-information',
            'general': 'https://www.example.com/more-information'
        }
    
    def extract_urls_from_content(self, content: str) -> List[str]:
        """Extract all URLs from blog content using regex patterns"""
        # Pattern to match URLs in markdown links and plain text
        url_patterns = [
            r'https?://[^\s\)\]\}]+',  # Plain URLs
            r'\[([^\]]+)\]\(([^)]+)\)',  # Markdown links [text](url)
        ]
        
        urls = []
        for pattern in url_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if len(match.groups()) > 1:
                    # Markdown link - get URL from second group
                    url = match.group(2)
                else:
                    # Plain URL
                    url = match.group(0)
                
                # Clean up URL
                url = url.strip('.,;!?)')
                if url and url.startswith(('http://', 'https://')):
                    urls.append(url)
        
        return list(set(urls))  # Remove duplicates
    
    def validate_url_with_analysis(self, url: str) -> URLAnalysis:
        """Validate a URL and return detailed analysis"""
        try:
            # Use the existing URL validation tool
            result_json = self.url_validator._run(url)
            import json
            result = json.loads(result_json)
            
            return URLAnalysis(
                original_url=url,
                is_working=result.get('accessible', False),
                status_code=result.get('status_code'),
                error=result.get('error')
            )
        except Exception as e:
            self.logger.error(f"URL validation failed for {url}: {e}")
            return URLAnalysis(
                original_url=url,
                is_working=False,
                status_code=None,
                error=f"Validation error: {str(e)}"
            )
    
    def find_working_alternative(self, broken_url: str) -> Optional[str]:
        """Attempt to find a working alternative for a broken URL"""
        parsed_url = urlparse(broken_url)
        domain = parsed_url.netloc.lower()
        
        # Remove www. prefix for matching
        clean_domain = domain.replace('www.', '')
        
        # Try domain alternatives
        if clean_domain in self.domain_alternatives:
            alternatives = self.domain_alternatives[clean_domain]
            
            for alt_domain in alternatives:
                # Construct alternative URL
                alt_url = f"{parsed_url.scheme}://{alt_domain}{parsed_url.path}"
                
                # Test if alternative works
                analysis = self.validate_url_with_analysis(alt_url)
                if analysis.is_working:
                    self.logger.info(f"Found working alternative: {alt_url} for {broken_url}")
                    return alt_url
        
        # Try common path fixes
        if parsed_url.path and len(parsed_url.path) > 1:
            # Try removing last path segment
            path_parts = parsed_url.path.split('/')
            if len(path_parts) > 2:
                simplified_path = '/'.join(path_parts[:-1])
                alt_url = f"{parsed_url.scheme}://{parsed_url.netloc}{simplified_path}"
                
                analysis = self.validate_url_with_analysis(alt_url)
                if analysis.is_working:
                    self.logger.info(f"Found working simplified URL: {alt_url} for {broken_url}")
                    return alt_url
        
        # Try just the domain root
        root_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
        analysis = self.validate_url_with_analysis(root_url)
        if analysis.is_working:
            self.logger.info(f"Found working root URL: {root_url} for {broken_url}")
            return root_url
        
        return None
    
    def get_appropriate_placeholder(self, url: str) -> str:
        """Get an appropriate placeholder URL based on content context"""
        url_lower = url.lower()
        
        if any(keyword in url_lower for keyword in ['climb', 'mountain', 'outdoor']):
            return self.placeholder_urls['climbing']
        elif any(keyword in url_lower for keyword in ['travel', 'tourism', 'visit']):
            return self.placeholder_urls['travel']
        elif any(keyword in url_lower for keyword in ['outdoor', 'activity']):
            return self.placeholder_urls['outdoor']
        elif any(keyword in url_lower for keyword in ['tourism', 'tourist']):
            return self.placeholder_urls['tourism']
        else:
            return self.placeholder_urls['general']
    
    def fix_broken_url(self, analysis: URLAnalysis) -> URLAnalysis:
        """Attempt to fix a broken URL"""
        if analysis.is_working:
            return analysis  # Already working
        
        # Try to find working alternative
        alternative = self.find_working_alternative(analysis.original_url)
        
        if alternative:
            analysis.replacement_url = alternative
            analysis.action_taken = "replaced"
            self.logger.info(f"Replaced broken URL {analysis.original_url} with {alternative}")
        else:
            # Use placeholder as last resort
            placeholder = self.get_appropriate_placeholder(analysis.original_url)
            analysis.replacement_url = placeholder
            analysis.action_taken = "replaced"
            self.logger.warning(f"Using placeholder for unfixable URL {analysis.original_url}")
        
        return analysis
    
    def apply_fixes_to_content(self, content: str, analyses: List[URLAnalysis]) -> str:
        """Apply URL fixes to the blog content"""
        modified_content = content
        
        for analysis in analyses:
            if analysis.action_taken == "replaced" and analysis.replacement_url:
                # Replace the original URL with the fixed URL
                modified_content = modified_content.replace(
                    analysis.original_url, 
                    analysis.replacement_url
                )
                self.logger.info(f"Applied fix: {analysis.original_url} → {analysis.replacement_url}")
            elif analysis.action_taken == "removed":
                # Remove broken URLs (implement if needed)
                pass
        
        return modified_content
    
    def run_quality_gate(self, blog_content: str) -> Tuple[str, QualityGateReport]:
        """
        Run the complete URL quality gate process on blog content.
        
        Returns:
            Tuple of (fixed_content, quality_report)
        """
        self.logger.info("🚨 RUNNING URL QUALITY GATE")
        
        # Step 1: Extract all URLs
        urls = self.extract_urls_from_content(blog_content)
        self.logger.info(f"📊 Found {len(urls)} URLs to validate")
        
        if not urls:
            # No URLs found, return original content
            report = QualityGateReport(
                total_urls_found=0,
                working_urls=0,
                broken_urls=0,
                urls_replaced=0,
                urls_removed=0,
                urls_fixed=0,
                analysis_results=[],
                content_modified=False
            )
            return blog_content, report
        
        # Step 2: Validate all URLs
        analyses = []
        for url in urls:
            self.logger.info(f"🔍 Validating: {url}")
            analysis = self.validate_url_with_analysis(url)
            analyses.append(analysis)
        
        # Step 3: Fix broken URLs
        fixed_analyses = []
        for analysis in analyses:
            if not analysis.is_working:
                self.logger.warning(f"❌ Broken URL found: {analysis.original_url}")
                fixed_analysis = self.fix_broken_url(analysis)
                fixed_analyses.append(fixed_analysis)
            else:
                self.logger.info(f"✅ Working URL: {analysis.original_url}")
                fixed_analyses.append(analysis)
        
        # Step 4: Apply fixes to content
        fixed_content = self.apply_fixes_to_content(blog_content, fixed_analyses)
        
        # Step 5: Generate quality report
        working_count = sum(1 for a in analyses if a.is_working)
        broken_count = len(analyses) - working_count
        replaced_count = sum(1 for a in fixed_analyses if a.action_taken == "replaced")
        removed_count = sum(1 for a in fixed_analyses if a.action_taken == "removed")
        fixed_count = replaced_count + removed_count
        
        report = QualityGateReport(
            total_urls_found=len(urls),
            working_urls=working_count,
            broken_urls=broken_count,
            urls_replaced=replaced_count,
            urls_removed=removed_count,
            urls_fixed=fixed_count,
            analysis_results=fixed_analyses,
            content_modified=(fixed_content != blog_content)
        )
        
        self.logger.info(f"🎯 Quality Gate Complete: {working_count}/{len(urls)} URLs working, {fixed_count} fixed")
        
        return fixed_content, report


def format_quality_report(report: QualityGateReport) -> str:
    """Format quality gate report for logging/display"""
    lines = [
        "🛡️ URL QUALITY GATE REPORT",
        "=" * 50,
        f"📊 Total URLs Found: {report.total_urls_found}",
        f"✅ Working URLs: {report.working_urls}",
        f"❌ Broken URLs: {report.broken_urls}",
        f"🔧 URLs Fixed: {report.urls_fixed}",
        f"📝 Content Modified: {'Yes' if report.content_modified else 'No'}",
        "",
        "🔍 Detailed Analysis:"
    ]
    
    for i, analysis in enumerate(report.analysis_results, 1):
        status = "✅ WORKING" if analysis.is_working else "❌ BROKEN"
        action = f" → {analysis.action_taken.upper()}" if analysis.action_taken != "none" else ""
        
        lines.append(f"{i:2d}. {status}{action}: {analysis.original_url}")
        
        if analysis.replacement_url and analysis.action_taken == "replaced":
            lines.append(f"    🔗 Fixed with: {analysis.replacement_url}")
        elif analysis.error:
            lines.append(f"    ⚠️  Error: {analysis.error}")
    
    return "\n".join(lines)