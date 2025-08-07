"""
Task Factory for Blog Generation

Creates specialized tasks for different phases of blog generation.
Follows Single Responsibility Principle - only creates and configures tasks.
"""

from crewai import Task, Agent
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class TaskFactory:
    """Factory for creating specialized tasks for blog generation phases."""
    
    @staticmethod
    def create_research_task(agent: Agent, topic: str, current_year: int) -> Task:
        """Create a research task for gathering information on a topic."""
        return Task(
            description=f"""Conduct comprehensive research on '{topic}' with focus on {current_year} developments.
            
            Your research should include:
            1. Latest trends and developments in {current_year}
            2. Key industry insights and expert opinions
            3. Statistical data and market analysis
            4. Real-world examples and case studies
            5. Future implications and predictions
            
            Ensure all information is current, credible, and relevant to {current_year}.
            Focus on actionable insights that would be valuable to readers.
            """,
            agent=agent,
            expected_output="""A comprehensive research report containing:
            - Executive summary of key findings
            - Detailed analysis with supporting data
            - Credible sources and references
            - Actionable insights and implications
            - Current trends and future outlook"""
        )
    
    @staticmethod
    def create_content_task(agent: Agent, topic: str, current_year: int) -> Task:
        """Create a content creation task for writing blog posts."""
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
            
            Use the research findings to create content that provides real value to readers.
            Include practical examples and actionable advice.
            """,
            agent=agent,
            expected_output="""A complete blog post with:
            - SEO-optimized title and meta description
            - Well-structured content with headers
            - Engaging introduction and conclusion
            - Actionable insights and examples
            - Image suggestions with descriptions
            - Natural keyword integration"""
        )
    
    @staticmethod
    def create_fact_check_task(agent: Agent, topic: str) -> Task:
        """Create a fact-checking task for verifying content accuracy."""
        return Task(
            description=f"""Thoroughly fact-check the blog post about '{topic}'.
            
            Verification process:
            1. Verify all statistical claims and data points
            2. Check accuracy of examples and case studies
            3. Validate technical information and terminology
            4. Ensure claims are properly supported
            5. Flag any questionable or unverified statements
            6. Suggest corrections or clarifications where needed
            
            Focus on maintaining content credibility while preserving readability.
            """,
            agent=agent,
            expected_output="""A fact-checked version with:
            - Verified accuracy of all claims
            - Corrected any inaccuracies
            - Added credibility markers where appropriate
            - Maintained original structure and flow
            - Clear notes on any changes made"""
        )
    
    @staticmethod
    def create_finalization_task(agent: Agent, topic: str) -> Task:
        """Create a finalization task for polishing content."""
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
            
            Deliver a publication-ready blog post that engages readers
            and provides exceptional value.
            """,
            agent=agent,
            expected_output="""A polished, publication-ready blog post with:
            - Perfect grammar and formatting
            - Engaging flow and readability
            - Consistent style throughout
            - Strong SEO optimization
            - Clean markdown structure
            - Professional presentation"""
        )
