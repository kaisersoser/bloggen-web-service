"""Task Factory for Blog Generation.

Creates specialized tasks for different phases of blog generation.
Follows Single Responsibility Principle - only creates and configures tasks.
"""

from crewai import Task, Agent
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class TaskFactory:
    """Factory for creating specialized tasks for blog generation phases."""
    
    @staticmethod
    def create_research_task(agent: Agent, topic: str, current_year: int, instructions: Optional[str] = None) -> Task:
        """Create a research task for gathering information on a topic."""
        extra = ("\n\nUSER DIRECTIVES (priority unless they conflict with sourcing rules):\n" + instructions.strip()) if instructions else ""
        return Task(
            description=f"""Conduct comprehensive research on '{topic}' with focus on {current_year} developments.

            MANDATORY INTERNET VALIDATION:
            - Use the available web research tools (e.g. Serper search) to gather CURRENT sources.
            - For every key fact, statistic, quote or market figure you include, capture the SOURCE URL.
            - Prefer primary / authoritative sources (official reports, reputable news, academic or vendor docs) over low‑credibility blogs.
            - Discard or flag information older than {current_year - 2} unless historically essential.

            Your research must include:
            1. Latest trends and developments in {current_year} (each trend must have at least one source link)
            2. Key industry insights and expert opinions (cite source links inline)
            3. Statistical data and market analysis (include exact numbers + source)
            4. Real-world examples and case studies (provide company / project link)
            5. Future implications and predictions (separate clearly from sourced factual data)

            OUTPUT REQUIREMENTS FOR SOURCING:
            - Inline cite each sourced fact using markdown link syntax: [Descriptive Source Title](https://example.com)
            - Maintain a running unique list of sources.
            - Provide at end a 'Sources' section: numbered list with one line per distinct URL.
            - Do NOT hallucinate URLs; if a claim cannot be sourced, explicitly mark it as UNSOURCED and minimize such claims.

            Ensure all information is current, credible, and relevant to {current_year}.
            Focus on actionable insights that would be valuable to readers.{extra}
            """,
            agent=agent,
            expected_output="""A comprehensive research report containing:
            - Executive summary of key findings (with inline markdown links for sourced claims)
            - Detailed analysis grouped by theme (each fact linked)
            - Explicit separation of sourced facts vs projections
            - Actionable insights and implications
            - Current trends and future outlook
            - 'Sources' section: numbered markdown list of unique source URLs used above"""
        )
    
    @staticmethod
    def create_content_task(agent: Agent, topic: str, current_year: int, instructions: Optional[str] = None) -> Task:
        """Create a content creation task for writing blog posts."""
        extra = ("\n\nUSER DIRECTIVES (priority unless they conflict with factual accuracy / sourcing):\n" + instructions.strip()) if instructions else ""
        return Task(
            description=f"""Create an engaging, SEO-optimized blog post about '{topic}' for {current_year}.
            
            Requirements:
            1. Title: Compelling and SEO-friendly
            2. Structure: Clear headers and subheadings
            3. Content: Informative, engaging, and actionable
            4. SEO: Natural keyword integration
            5. Length: 1500-2000 words
            6. Images: Include relevant image suggestions with descriptions
            7. Tone: Professional yet conversational
            8. SOURCING: Preserve all validated source links from research; any fact carried over must retain its markdown link.
            9. REFERENCES: End with a 'References' section (numbered) mirroring unique sources actually cited in the body.
            10. If a claim from research lacks a link, either add one via new search (using tools) or omit the claim.
            
            Use the research findings to create content that provides real value to readers.
            Include practical examples and actionable advice.{extra}
            """,
            agent=agent,
            expected_output="""A complete blog post with:
            - SEO-optimized title and meta description
            - Well-structured content with headers
            - Engaging introduction and conclusion
            - Actionable insights and examples (each factually grounded claim linked)
            - Image suggestions with descriptions
            - Natural keyword integration
            - Inline markdown hyperlinks for every sourced fact
            - Final 'References' section: numbered unique sources referenced above (no duplicates)"""
        )

    @staticmethod
    def create_fact_check_task(agent: Agent, topic: str, instructions: Optional[str] = None) -> Task:
        """Create a fact-checking task for verifying content accuracy with live re-validation."""
        extra = ("\n\nUSER ORIGINAL DIRECTIVES (retain intent while enforcing verification):\n" + instructions.strip()) if instructions else ""
        return Task(
            description=f"""Thoroughly fact-check the blog post about '{topic}'.

            LIVE RE-VALIDATION (MANDATORY): Use the provided web research/search tool(s) to re-check every statistic, date, numeric metric, market figure, quote, and technical claim.
            For each claim:
              - Confirm the link is still valid and authoritative.
              - Replace broken / low-credibility sources with better ones.
              - Add missing links where claims lack sourcing (search for them; if no credible source found, mark the claim UNSOURCED and recommend removal or rewrite).

            Verification process:
            1. Re-verify all statistical claims (ensure numbers & units match current context)
            2. Confirm examples & case studies still accurate / up to date
            3. Validate technical terminology and version references
            4. Ensure EVERY factual sentence has an inline markdown link (except clearly marked opinion / synthesis)
            5. Flag outdated (>2 years) data unless historically framed
            6. Provide a concise correction log summarizing changes

            Output MUST keep existing structure but update references accordingly.{extra}
            """,
            agent=agent,
            expected_output="""A fact-checked version with:
            - All factual claims verified with current sources
            - Added / updated inline links where missing or weak
            - Outdated or unsourced claims flagged or revised
            - Consolidated, deduplicated 'References' section (numbered)
            - A short 'Fact Check Summary' section listing corrections & replaced sources"""
        )

    @staticmethod
    def create_finalization_task(agent: Agent, topic: str, instructions: Optional[str] = None) -> Task:
        """Create a finalization task for polishing content."""
        extra = ("\n\nUSER DIRECTIVES (final polish should respect these preferences):\n" + instructions.strip()) if instructions else ""
        return Task(
            description=f"""Finalize the blog post about '{topic}' for publication.
            
            Finalization requirements:
            1. Perfect grammar and spelling
            2. Consistent formatting and style
            3. Optimal content flow and readability
            4. Engaging transitions between sections
            5. Strong introduction and conclusion
            6. Clean markdown formatting
            7. Final SEO optimization
            8. Validate that every factual claim retains a hyperlink; no orphan references.
            9. Ensure 'References' section exists, numbered, unique, sorted by first appearance.
            10. Do NOT remove links; only fix formatting or obvious duplicates.
            
            Deliver a publication-ready blog post that engages readers
            and provides exceptional value.{extra}
            """,
            agent=agent,
            expected_output="""A polished, publication-ready blog post with:
            - Perfect grammar and formatting
            - Engaging flow and readability
            - Consistent style throughout
            - Strong SEO optimization
            - Clean markdown structure
            - Professional presentation
            - Inline citations preserved & cleaned
            - Final 'References' section (numbered, unique, valid URLs)"""
        )
