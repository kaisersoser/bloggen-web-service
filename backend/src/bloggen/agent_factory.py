"""
Agent Factory for Blog Generation

Creates specialized AI agents for different phases of blog generation.
Follows Single Responsibility Principle - only creates and configures agents.
"""

from crewai import Agent
from typing import List, Any
import logging

# Import configuration for model settings
from core.config import config

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating specialized AI agents for blog generation."""
    
    @staticmethod
    def create_researcher(tools: List[Any]) -> Agent:
        """Create a research agent for gathering information."""
        return Agent(
            role='Senior Researcher',
            goal='Uncover cutting-edge developments and insights in the given topic',
            verbose=True,
            backstory="""You work at a leading tech think tank.
            Your expertise lies in identifying emerging trends and analyzing complex topics.
            You're known for your ability to find credible sources and synthesize information
            into valuable insights that drive strategic decisions.""",
            tools=tools,
            allow_delegation=False,
            llm=config.models.research_model  # Use gpt-4o for research tasks
        )
    
    @staticmethod
    def create_content_creator(tools: List[Any]) -> Agent:
        """Create a content creation agent for writing blog posts."""
        return Agent(
            role='Tech Content Creator',
            goal='Transform research insights into compelling, SEO-optimized blog content',
            verbose=True,
            backstory="""You are a seasoned tech content creator with a knack for making
            complex topics accessible and engaging. Your writing style is conversational
            yet authoritative, and you always include relevant examples and practical insights.
            You understand SEO principles and know how to structure content for maximum impact.""",
            tools=tools,
            allow_delegation=False,
            llm=config.models.content_model  # Use gpt-4o-mini for content generation
        )
    
    @staticmethod
    def create_fact_checker(tools: List[Any]) -> Agent:
        """Create a fact-checking agent for verifying content accuracy with live web validation."""
        return Agent(
            role='Senior Fact Checker',
            goal='Verify the accuracy of claims and ensure content credibility',
            verbose=True,
            backstory="""You are a meticulous fact-checker with years of experience in
            journalism and content verification. Your sharp eye for detail and commitment to
            accuracy ensures that all published content meets the highest standards of
            credibility and reliability.""",
            tools=tools,  # Provide web search tools for live source re-validation
            allow_delegation=False,
            llm=config.models.fact_check_model  # Use gpt-4o for fact checking
        )
    
    @staticmethod
    def create_finalizer() -> Agent:
        """Create a finalization agent for polishing content."""
        return Agent(
            role='Editorial Finalizer',
            goal='Polish content to publication standards with perfect formatting',
            verbose=True,
            backstory="""You are an experienced editor who specializes in preparing content
            for publication. Your expertise lies in refining structure, improving readability,
            and ensuring consistent formatting. You have a keen eye for flow and always
            deliver content that engages readers from start to finish.""",
            tools=[],
            allow_delegation=False,
            llm=config.models.finalization_model  # Use gpt-4o-mini for finalization
        )
