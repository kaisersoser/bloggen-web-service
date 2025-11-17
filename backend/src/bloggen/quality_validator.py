"""
Quality Validation Gates

Enforces minimum quality standards between workflow phases.
Provides automated validation with retry logic and detailed feedback.
"""

import logging
import re
from typing import Tuple, List, Optional, Dict, Any
from .schemas.research_schema import StructuredResearchOutput

logger = logging.getLogger(__name__)


class QualityValidator:
    """Validates content quality at different workflow stages"""

    @staticmethod
    def validate_research_quality(
        structured_research: Optional[StructuredResearchOutput],
    ) -> Tuple[bool, List[str], Dict[str, int]]:
        """
        Validate research phase output meets minimum standards.

        Args:
            structured_research: Parsed structured research output

        Returns:
            Tuple of (is_valid, issues_list, metrics_dict)
        """
        if not structured_research:
            return False, ["Research output is None or failed to parse"], {}

        # Use built-in validation
        is_valid, issues = structured_research.validate_minimums()

        # Get comprehensive metrics
        metrics = structured_research.get_quality_metrics()

        if not is_valid:
            logger.warning(f"Research validation failed: {len(issues)} issues found")
            for issue in issues:
                logger.warning(f"  - {issue}")

        return is_valid, issues, metrics

    @staticmethod
    def validate_content_quality(
        content: str,
        structured_research: Optional[StructuredResearchOutput] = None,
        min_words: int = 1000,
        min_paragraphs: int = 8,
        min_sections: int = 4,
        min_citations: int = 5,
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate content generation output meets minimum standards.

        Args:
            content: Generated blog content
            structured_research: Optional research data for validation
            min_words: Minimum word count
            min_paragraphs: Minimum paragraph count
            min_sections: Minimum section count (headers)
            min_citations: Minimum citation count

        Returns:
            Tuple of (is_valid, issues_list, metrics_dict)
        """
        issues = []

        # Word count
        words = content.split()
        word_count = len(words)
        if word_count < min_words:
            issues.append(f"Insufficient word count: {word_count}/{min_words} minimum")

        # Paragraph count (double newline separated)
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        paragraph_count = len(paragraphs)
        if paragraph_count < min_paragraphs:
            issues.append(
                f"Insufficient paragraphs: {paragraph_count}/{min_paragraphs} minimum"
            )

        # Section count (markdown headers)
        sections = re.findall(r"^#+\s+.+$", content, re.MULTILINE)
        section_count = len(sections)
        if section_count < min_sections:
            issues.append(
                f"Insufficient sections: {section_count}/{min_sections} minimum"
            )

        # Citation density (check for markdown links)
        citations = re.findall(r"\[([^\]]+)\]\(([^\)]+)\)", content)
        citation_count = len(citations)
        citation_density = (
            citation_count / max(word_count / 300, 1)
        )  # Citations per 300 words

        if citation_count < min_citations:
            issues.append(
                f"Insufficient citations: {citation_count}/{min_citations} minimum"
            )

        if citation_density < 0.5:
            issues.append(
                f"Low citation density: {citation_density:.2f} (expect >0.5 per 300 words)"
            )

        # Check for hallucination patterns
        hallucination_patterns = [
            r"according to (?:a |an |the )?(?:recent )?(?:study|report|research)(?! \[)",  # "according to a study" without citation
            r"(?:recent|new) (?:studies|research) shows?(?! \[)",  # "recent studies show" without citation
            r"\d+%(?! of)(?!.*\[.{0,50})",  # Percentage without citation within 50 chars
            r"experts? (?:say|believe|think)(?! \[)",  # "experts say" without citation
        ]

        hallucination_count = 0
        for pattern in hallucination_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            hallucination_count += len(matches)

        if hallucination_count > 3:
            issues.append(
                f"Potential hallucinations detected: {hallucination_count} uncited claims"
            )

        # Quality score calculation
        quality_score = QualityValidator._calculate_content_score(
            word_count,
            paragraph_count,
            section_count,
            citation_count,
            hallucination_count,
        )

        # Quality metrics
        metrics = {
            "word_count": word_count,
            "paragraph_count": paragraph_count,
            "section_count": section_count,
            "citation_count": citation_count,
            "citation_density": round(citation_density, 2),
            "hallucination_flags": hallucination_count,
            "quality_score": round(quality_score, 1),
        }

        is_valid = len(issues) == 0

        if not is_valid:
            logger.warning(f"Content validation failed: {len(issues)} issues found")
            for issue in issues:
                logger.warning(f"  - {issue}")
        else:
            logger.info(f"✅ Content validation passed: Quality score {quality_score:.1f}/10")

        return is_valid, issues, metrics

    @staticmethod
    def _calculate_content_score(
        word_count: int,
        paragraph_count: int,
        section_count: int,
        citation_count: int,
        hallucination_count: int,
    ) -> float:
        """
        Calculate 0-10 quality score based on content metrics.

        Args:
            word_count: Total words in content
            paragraph_count: Number of paragraphs
            section_count: Number of sections/headers
            citation_count: Number of citations
            hallucination_count: Number of uncited claims

        Returns:
            Quality score from 0.0 to 10.0
        """
        score = 0.0

        # Word count (0-3 points)
        if word_count >= 2000:
            score += 3.0
        elif word_count >= 1500:
            score += 2.5
        elif word_count >= 1000:
            score += 2.0
        elif word_count >= 800:
            score += 1.0

        # Structure (0-3 points)
        if paragraph_count >= 15 and section_count >= 6:
            score += 3.0
        elif paragraph_count >= 10 and section_count >= 4:
            score += 2.5
        elif paragraph_count >= 8 and section_count >= 4:
            score += 2.0
        elif paragraph_count >= 5 and section_count >= 3:
            score += 1.0

        # Citations (0-3 points)
        if citation_count >= 10:
            score += 3.0
        elif citation_count >= 7:
            score += 2.0
        elif citation_count >= 5:
            score += 1.0

        # Readability bonus (0-1 point)
        avg_paragraph_length = word_count / max(paragraph_count, 1)
        if 50 <= avg_paragraph_length <= 150:  # Optimal paragraph length
            score += 1.0

        # Penalty for hallucinations (up to -2 points)
        score -= min(hallucination_count * 0.5, 2.0)

        return max(0.0, min(10.0, score))

    @staticmethod
    def generate_feedback_message(
        issues: List[str], metrics: Dict[str, Any], phase: str = "content"
    ) -> str:
        """
        Generate detailed feedback message for retry attempts.

        Args:
            issues: List of validation issues
            metrics: Quality metrics dictionary
            phase: Phase name (research/content)

        Returns:
            Formatted feedback message
        """
        feedback = f"⚠️ QUALITY ISSUES FROM PREVIOUS {phase.upper()} ATTEMPT:\n\n"

        for i, issue in enumerate(issues, 1):
            feedback += f"{i}. {issue}\n"

        feedback += f"\n📊 CURRENT METRICS:\n"
        for key, value in metrics.items():
            feedback += f"  - {key.replace('_', ' ').title()}: {value}\n"

        if phase == "content":
            word_count = metrics.get('word_count', 0)
            words_needed = max(0, 1000 - word_count)
            
            feedback += f"\n🎯 CRITICAL REQUIREMENTS YOU MUST MEET:\n"
            feedback += f"  - MINIMUM 1000 words (YOU HAVE: {word_count} words)\n"
            if words_needed > 0:
                feedback += f"  - YOU NEED: {words_needed} MORE WORDS\n"
            feedback += "  - MINIMUM 8 paragraphs (4-6 sentences each, 80-120 words per paragraph)\n"
            feedback += "  - MINIMUM 4 sections with H2 headers (## Section Title)\n"
            feedback += "  - MINIMUM 5 citations with real URLs\n"
            feedback += "  - Quality score target: 5/10\n"
            feedback += "\n🚨 CRITICAL ACTION REQUIRED:\n"
            if words_needed > 0:
                feedback += f"Your content is {words_needed} words SHORT. To fix this:\n"
                feedback += "1. EXPAND each existing section by 100-200 words with specific examples\n"
                feedback += "2. ADD 1-2 new sections with detailed explanations (200-300 words each)\n"
                feedback += "3. ELABORATE on key points - don't just state facts, EXPLAIN them\n"
                feedback += "4. ADD specific examples with company names, data, and details\n"
                feedback += "5. INCLUDE case studies and real-world applications\n\n"
            feedback += "DO NOT just add fluff - add SUBSTANTIVE content with depth and examples."

        return feedback
