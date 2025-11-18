"""
Citation Tracker Utility

Tracks citations in blog content to help agents monitor and improve citation density.
Part of Phase 1 Agent Efficiency Improvements.
"""

import re
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class CitationTracker:
    """Tracks citations in markdown content and provides feedback."""

    def __init__(self):
        self.used_citations: List[Dict[str, str]] = []
        self.citation_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    def track_content(self, content: str) -> Dict[str, any]:
        """
        Analyze content for citations and return statistics.
        
        Args:
            content: Markdown content to analyze
            
        Returns:
            Dictionary with citation statistics
        """
        # Find all markdown links
        matches = self.citation_pattern.findall(content)
        
        # Clear previous tracking
        self.used_citations = []
        
        # Track unique citations
        seen_urls = set()
        for text, url in matches:
            if url not in seen_urls and not url.startswith('#'):  # Exclude anchor links
                self.used_citations.append({
                    'text': text,
                    'url': url
                })
                seen_urls.add(url)
        
        # Calculate statistics
        citation_count = len(self.used_citations)
        word_count = len(content.split())
        citation_density = (citation_count / word_count * 100) if word_count > 0 else 0
        
        return {
            'citation_count': citation_count,
            'word_count': word_count,
            'citation_density': citation_density,
            'citations': self.used_citations
        }

    def generate_feedback(self, content: str, target_citations: int = 5) -> str:
        """
        Generate feedback message for agent about citation usage.
        
        Args:
            content: Markdown content to analyze
            target_citations: Minimum number of citations expected
            
        Returns:
            Formatted feedback string
        """
        stats = self.track_content(content)
        citation_count = stats['citation_count']
        word_count = stats['word_count']
        
        if citation_count >= target_citations:
            status = "✅ EXCELLENT"
            message = f"You have {citation_count} citations - great job backing up your claims!"
        elif citation_count >= target_citations - 2:
            status = "⚠️ GOOD"
            needed = target_citations - citation_count
            message = f"You have {citation_count} citations. Add {needed} more to reach the target of {target_citations}."
        else:
            status = "❌ INSUFFICIENT"
            needed = target_citations - citation_count
            message = f"You only have {citation_count} citations. You need {needed} more to meet the minimum of {target_citations}."
        
        feedback = f"""
📚 CITATION TRACKER REPORT:
Status: {status}
Citations Found: {citation_count}/{target_citations}
Word Count: {word_count}
Citation Density: {stats['citation_density']:.2f}%

{message}

Remember: Use markdown format [descriptive text](https://url.com) for all citations.
Every statistic, claim, or data point should have a citation.
"""
        return feedback

    def get_citation_report(self) -> str:
        """Generate a detailed report of all tracked citations."""
        if not self.used_citations:
            return "No citations tracked yet."
        
        report = f"📚 CITATION REPORT: {len(self.used_citations)} citations found\n\n"
        for i, citation in enumerate(self.used_citations, 1):
            report += f"{i}. [{citation['text']}]({citation['url']})\n"
        
        return report

    def validate_citation_format(self, content: str) -> Tuple[bool, List[str]]:
        """
        Validate that citations follow proper markdown format.
        
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for bare URLs (not in markdown format)
        bare_url_pattern = re.compile(r'(?<!\()https?://[^\s)]+(?!\))')
        bare_urls = bare_url_pattern.findall(content)
        
        if bare_urls:
            issues.append(f"Found {len(bare_urls)} bare URLs not in markdown format. Wrap them in [text](url) format.")
        
        # Check for numbered citations like [1], [2] without URLs
        numbered_pattern = re.compile(r'\[\d+\](?!\()')
        numbered_refs = numbered_pattern.findall(content)
        
        if numbered_refs:
            issues.append(f"Found {len(numbered_refs)} numbered references like [1] without URLs. Use [text](url) format instead.")
        
        is_valid = len(issues) == 0
        return is_valid, issues


# Global citation tracker instance for convenience
_global_tracker = CitationTracker()


def track_citations(content: str) -> Dict[str, any]:
    """Convenience function to track citations using global tracker."""
    return _global_tracker.track_content(content)


def get_citation_feedback(content: str, target_citations: int = 5) -> str:
    """Convenience function to get citation feedback using global tracker."""
    return _global_tracker.generate_feedback(content, target_citations)
