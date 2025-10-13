"""
Content Integrity Validator - Removes hallucinated content and invalid references.

This tool provides aggressive content validation by:
1. Identifying invalid, generic, or placeholder URLs in references
2. Removing sentences and paragraphs that cite invalid references
3. Removing invalid reference entries entirely
4. Renumbering remaining references sequentially
5. Preserving only content backed by legitimate, specific sources

This approach ensures content quality by removing potentially hallucinated
information rather than masking it with placeholder URLs.
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Set
from urllib.parse import urlparse
from dataclasses import dataclass
from .url_validation_tool import URLValidationTool


@dataclass
class ReferenceAnalysis:
    """Analysis result for a single reference"""

    reference_number: str
    title: str
    url: str
    is_valid: bool
    is_specific: bool
    validation_error: Optional[str]
    issues: List[str]
    action: str  # "keep", "remove"


@dataclass
class ContentIntegrityReport:
    """Report of content integrity validation actions"""

    total_references: int
    valid_references: int
    removed_references: int
    content_sentences_removed: int
    content_paragraphs_removed: int
    content_quality_score: float  # Percentage of content kept
    reference_analyses: List[ReferenceAnalysis]
    removed_content_snippets: List[str]


class ContentIntegrityValidator:
    """
    Aggressive content validator that removes hallucinated content entirely.

    Unlike URL replacement strategies, this validator removes sentences and
    references that are backed by invalid sources, ensuring content integrity.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.url_validator = URLValidationTool()

        # Patterns that indicate placeholder or generic URLs
        self.placeholder_indicators = [
            "example.com",
            "example.org",
            "placeholder",
            "more-information",
            "sample-url",
        ]

        # Generic URL patterns that suggest hallucination
        self.generic_url_patterns = [
            r"^https?://[^/]+/?$",  # Just domain with optional trailing slash
            r"^https?://www\.[^/]+/?$",  # www.domain.com only
        ]

        # Minimum path depth for specific URLs
        self.min_path_segments = 2

    def extract_references(self, content: str) -> List[Dict]:
        """Extract all numbered references from the references section"""
        references = []

        # Find references section
        ref_section_match = re.search(r"## References\s*\n(.+)", content, re.DOTALL)
        if not ref_section_match:
            self.logger.warning("No References section found")
            return references

        ref_section = ref_section_match.group(1)

        # Extract numbered reference lines
        ref_lines = [
            line.strip()
            for line in ref_section.split("\n")
            if line.strip() and re.match(r"^\d+\.", line.strip())
        ]

        for line in ref_lines:
            # Extract reference number, title, and URL
            match = re.match(r"^(\d+)\.\s+(.+?)\s+\[(.+?)\]", line)
            if match:
                references.append(
                    {
                        "number": match.group(1),
                        "title": match.group(2),
                        "url": match.group(3),
                        "full_line": line,
                    }
                )
            else:
                self.logger.warning(f"Could not parse reference line: {line}")

        return references

    def is_placeholder_url(self, url: str) -> bool:
        """Check if URL is a placeholder or example URL"""
        url_lower = url.lower()
        return any(indicator in url_lower for indicator in self.placeholder_indicators)

    def is_generic_url(self, url: str) -> bool:
        """Check if URL is too generic to be a legitimate source"""
        # Check against generic patterns
        for pattern in self.generic_url_patterns:
            if re.match(pattern, url):
                return True

        # Check path depth - URLs with no specific path are suspicious
        parsed = urlparse(url)
        path_segments = [seg for seg in parsed.path.split("/") if seg]

        # Exception for specific domains that can have short paths
        trusted_short_domains = ["population.un.org", "unhabitat.org", "worldbank.org"]

        domain = parsed.netloc.lower()
        if any(trusted in domain for trusted in trusted_short_domains):
            return False

        return len(path_segments) < self.min_path_segments

    def validate_url_accessibility(self, url: str) -> Tuple[bool, Optional[str]]:
        """Validate if URL is accessible"""
        try:
            result_json = self.url_validator._run(url)
            import json

            result = json.loads(result_json)
            return result.get("accessible", False), result.get("error")
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def analyze_reference(self, ref_dict: Dict) -> ReferenceAnalysis:
        """Analyze a single reference for validity and specificity"""
        url = ref_dict["url"]
        issues = []

        # Check for placeholder URLs
        if self.is_placeholder_url(url):
            issues.append("Placeholder URL detected")

        # Check for generic URLs
        if self.is_generic_url(url):
            issues.append("Generic/non-specific URL")

        # Validate URL accessibility
        is_accessible, validation_error = self.validate_url_accessibility(url)
        if not is_accessible:
            issues.append(f"URL not accessible: {validation_error}")

        # Determine if reference should be kept
        is_valid = is_accessible and not self.is_placeholder_url(url)
        is_specific = not self.is_generic_url(url)
        should_keep = is_valid and is_specific

        return ReferenceAnalysis(
            reference_number=ref_dict["number"],
            title=ref_dict["title"],
            url=url,
            is_valid=is_accessible,
            is_specific=is_specific,
            validation_error=validation_error,
            issues=issues,
            action="keep" if should_keep else "remove",
        )

    def find_content_citing_references(
        self, content: str, ref_numbers: Set[str]
    ) -> List[str]:
        """Find all content elements (sentences/paragraphs) that cite specific references"""
        citing_content = []

        # Get content before references section
        content_before_refs = content.split("## References")[0]

        # Split into paragraphs first
        paragraphs = content_before_refs.split("\n\n")

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # Check if paragraph cites any of the problematic references
            for ref_num in ref_numbers:
                if f"[{ref_num}]" in paragraph:
                    citing_content.append(paragraph)
                    break  # Don't double-count paragraphs

        return citing_content

    def remove_citing_content(self, content: str, problematic_refs: Set[str]) -> str:
        """Remove content that cites problematic references"""
        # Get content before references section
        parts = content.split("## References")
        if len(parts) != 2:
            return content

        content_part = parts[0]
        references_part = parts[1]

        # Split into paragraphs
        paragraphs = content_part.split("\n\n")
        clean_paragraphs = []

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # Check if paragraph cites problematic references
            cites_problematic = any(
                f"[{ref_num}]" in paragraph for ref_num in problematic_refs
            )

            if not cites_problematic:
                clean_paragraphs.append(paragraph)
            else:
                self.logger.info(
                    f"Removing paragraph citing refs {[r for r in problematic_refs if f'[{r}]' in paragraph]}: {paragraph[:100]}..."
                )

        # Reconstruct content
        clean_content = "\n\n".join(clean_paragraphs)
        return clean_content + "\n\n## References" + references_part

    def remove_invalid_references(
        self, content: str, analyses: List[ReferenceAnalysis]
    ) -> str:
        """Remove invalid reference entries and renumber remaining ones"""
        # Get valid references
        valid_analyses = [a for a in analyses if a.action == "keep"]

        if not valid_analyses:
            # No valid references - remove entire references section
            return content.split("## References")[0].rstrip()

        # Build new references section
        new_ref_lines = []
        old_to_new_mapping = {}

        for i, analysis in enumerate(valid_analyses, 1):
            old_to_new_mapping[analysis.reference_number] = str(i)
            new_ref_lines.append(f"{i}. {analysis.title} [{analysis.url}]")

        # Update citation numbers in content
        content_before_refs = content.split("## References")[0]

        for old_num, new_num in old_to_new_mapping.items():
            content_before_refs = content_before_refs.replace(
                f"[{old_num}]", f"[{new_num}]"
            )

        # Construct final content
        new_references_section = "\n".join(new_ref_lines)
        final_content = (
            f"{content_before_refs}\n\n## References\n\n{new_references_section}"
        )

        return final_content

    def validate_content_integrity(
        self, blog_content: str
    ) -> Tuple[str, ContentIntegrityReport]:
        """
        Run complete content integrity validation.

        Returns:
            Tuple of (cleaned_content, integrity_report)
        """
        self.logger.info("🔍 RUNNING CONTENT INTEGRITY VALIDATION")

        # Step 1: Extract references
        references = self.extract_references(blog_content)
        if not references:
            # No references to validate
            report = ContentIntegrityReport(
                total_references=0,
                valid_references=0,
                removed_references=0,
                content_sentences_removed=0,
                content_paragraphs_removed=0,
                content_quality_score=100.0,
                reference_analyses=[],
                removed_content_snippets=[],
            )
            return blog_content, report

        self.logger.info(f"📊 Found {len(references)} references to validate")

        # Step 2: Analyze each reference
        analyses = []
        for ref in references:
            self.logger.info(f"🔍 Analyzing reference {ref['number']}: {ref['url']}")
            analysis = self.analyze_reference(ref)
            analyses.append(analysis)

            if analysis.action == "remove":
                issues_str = ", ".join(analysis.issues)
                self.logger.warning(
                    f"❌ Reference {ref['number']} marked for removal: {issues_str}"
                )
            else:
                self.logger.info(f"✅ Reference {ref['number']} is valid")

        # Step 3: Identify problematic reference numbers
        problematic_refs = {
            a.reference_number for a in analyses if a.action == "remove"
        }
        self.logger.info(f"🗑️ Removing references: {list(problematic_refs)}")

        # Step 4: Find content citing problematic references
        citing_content = self.find_content_citing_references(
            blog_content, problematic_refs
        )
        self.logger.info(
            f"🗑️ Found {len(citing_content)} content elements citing problematic references"
        )

        # Step 5: Remove problematic content
        cleaned_content = self.remove_citing_content(blog_content, problematic_refs)

        # Step 6: Remove invalid references and renumber
        final_content = self.remove_invalid_references(cleaned_content, analyses)

        # Step 7: Generate report
        valid_count = len([a for a in analyses if a.action == "keep"])
        removed_count = len([a for a in analyses if a.action == "remove"])
        quality_score = (valid_count / len(analyses)) * 100 if analyses else 100

        report = ContentIntegrityReport(
            total_references=len(references),
            valid_references=valid_count,
            removed_references=removed_count,
            content_sentences_removed=0,  # We remove paragraphs, not individual sentences
            content_paragraphs_removed=len(citing_content),
            content_quality_score=quality_score,
            reference_analyses=analyses,
            removed_content_snippets=[c[:100] + "..." for c in citing_content],
        )

        self.logger.info(
            f"✅ Content Integrity Validation Complete: {quality_score:.1f}% content quality"
        )

        return final_content, report


def format_integrity_report(report: ContentIntegrityReport) -> str:
    """Format content integrity report for logging/display"""
    lines = [
        "🔍 CONTENT INTEGRITY VALIDATION REPORT",
        "=" * 60,
        f"📊 Total References Analyzed: {report.total_references}",
        f"✅ Valid References Kept: {report.valid_references}",
        f"❌ Invalid References Removed: {report.removed_references}",
        f"🗑️ Content Paragraphs Removed: {report.content_paragraphs_removed}",
        f"📈 Content Quality Score: {report.content_quality_score:.1f}%",
        "",
        "🔍 Reference Analysis:",
    ]

    for analysis in report.reference_analyses:
        status = "✅ KEPT" if analysis.action == "keep" else "❌ REMOVED"
        lines.append(f"  {analysis.reference_number:2s}. {status}: {analysis.url}")

        if analysis.issues:
            for issue in analysis.issues:
                lines.append(f"      ⚠️  {issue}")

    if report.removed_content_snippets:
        lines.extend(
            [
                "",
                "🗑️ Removed Content Snippets:",
                *[f"  • {snippet}" for snippet in report.removed_content_snippets[:5]],
            ]
        )

        if len(report.removed_content_snippets) > 5:
            lines.append(f"  • ... and {len(report.removed_content_snippets) - 5} more")

    return "\n".join(lines)
