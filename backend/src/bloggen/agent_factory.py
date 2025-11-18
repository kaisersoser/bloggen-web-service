"""
Agent Factory for Blog Generation

Creates specialized AI agents for different phases of blog generation.
Follows Single Responsibility Principle - only creates and configures agents.
"""

from crewai import Agent, LLM
from typing import List, Any, Optional
from datetime import datetime
import logging

# Import configuration for model settings
from core.config import config

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating specialized AI agents for blog generation."""

    @staticmethod
    def _create_llm(model_name: str) -> LLM:
        """Create an LLM object with proper configuration for any model provider.

        The model_name should include the provider prefix (e.g., 'gemini/model', 'openai/model')
        as specified in the environment configuration.
        """
        # Extract provider from model name to determine which API key to use
        if "/" in model_name:
            provider = model_name.split("/")[0].lower()
        else:
            provider = "openai"  # Default to OpenAI for backwards compatibility

        if provider == "gemini":
            return LLM(model=model_name, api_key=config.api.google_key)
        elif provider in ["openai", "gpt"]:
            return LLM(model=model_name, api_key=config.api.openai_key)
        elif provider == "anthropic":
            return LLM(model=model_name, api_key=config.api.anthropic_key)
        else:
            # For other providers, rely on environment variables or default configuration
            return LLM(model=model_name)

    @staticmethod
    def create_researcher(
        tools: List[Any], current_year: Optional[int] = None
    ) -> Agent:
        """Create a research agent for gathering information."""
        year = current_year if current_year else datetime.now().year
        year_context = (
            f" It is currently {year}, and you must focus on the most current developments and trends as of this year."
            if current_year
            else ""
        )
        return Agent(
            role="Senior Researcher",
            goal="Conduct deep, comprehensive research using web tools to uncover specific, detailed, and current information on the given topic",
            verbose=True,
            backstory=f"""You are a meticulous senior researcher at a leading tech think tank, known for your 
            thoroughness and attention to detail. You NEVER rely on general knowledge - you always use your 
            web research tools extensively to find the most current, specific information available.
            
            Your research methodology:
            - Execute multiple targeted web searches to gather comprehensive data
            - Always seek out SPECIFIC details: exact numbers, dates, company names, product versions
            - Prioritize authoritative sources: research papers, official documentation, industry reports
            - Extract measurable outcomes and concrete examples from case studies
            - Capture full expert quotes with proper attribution
            - Verify every fact with a credible source URL
            
            You take pride in delivering research that is:
            - SPECIFIC (not vague or generic)
            - CURRENT (from {year} or {year - 1})
            - DETAILED (enough to support a comprehensive 2000+ word article)
            - SOURCED (every claim backed by a credible URL)
            
            Your expertise lies in transforming broad topics into detailed, actionable research 
            that provides writers with concrete facts, statistics, quotes, and examples they can 
            immediately use. You understand that quality research is the foundation of quality content.{year_context}""",
            tools=tools,
            allow_delegation=False,
            llm=AgentFactory._create_llm(config.models.research_model),
        )

    @staticmethod
    def create_content_creator(
        tools: List[Any], current_year: Optional[int] = None
    ) -> Agent:
        """Create a content creation agent for writing blog posts."""
        year_context = (
            f" It is currently {current_year}, and you should write content that reflects the current state of technology and industry trends as of this year."
            if current_year
            else ""
        )
        return Agent(
            role="Tech Content Creator & Visual Storyteller",
            goal="Transform research insights into compelling, visually-rich blog content with 2-3 strategically placed, highly relevant images using intelligent tool selection",
            verbose=True,
            backstory=f"""You are a seasoned tech content creator who understands that great blog posts 
            combine excellent writing with HIGHLY RELEVANT visuals. Your expertise lies in creating content 
            that not only informs but visually enhances readers' understanding through strategic, contextual imagery.{year_context}
            
            You excel at:
            - Writing conversational yet authoritative content
            - Strategic image placement for maximum visual impact and relevance
            - Creating visual narratives that directly support and illustrate the written content
            - Ensuring images are contextually appropriate and add real value
            - Understanding SEO principles and content structure
            - Making complex topics accessible through both text and highly relevant visuals
            
            🚨 CRITICAL IMAGE SELECTION STRATEGY: 
            - You MUST include 2-3 HIGHLY RELEVANT, PHOTOREALISTIC images in EVERY blog post
            - PHOTOREALISTIC QUALITY: Prioritize professional, stylish, photo-quality images that directly relate to your content
            - The enhanced unsplash_image_search tool automatically generates photorealistic AI images when Unsplash photos aren't relevant enough
            - Use MULTIPLE SPECIFIC KEYWORDS for better image relevance (3-5 keywords per query)
            - For abstract concepts, the tool will automatically generate photorealistic AI illustrations
            - For real-world applications, the tool prioritizes high-quality Unsplash photography
            - ALWAYS ensure images are visually striking, modern, and directly relevant to your content
            
            🎯 OPTIMAL PHOTOREALISTIC IMAGE QUERY FORMULA:
            [Domain Context] + [Specific Subject] + [Visual Style Modifiers]
            
            Example: "healthcare AI diagnosis doctor technology modern" 
            NOT just: "AI" or "healthcare"
            
            1. HERO IMAGE: 
               - Use 4-5 keywords: [main topic] + [industry] + "professional modern photorealistic"
               - Example: "artificial intelligence healthcare diagnosis professional modern"
            
            2. SUPPORTING IMAGES: 
               - Use 3-5 keywords specific to each section
               - Include domain context + technical specifics
               - Example: "financial trading algorithm dashboard analytics professional"
            
            3. TRUST THE ENHANCED TOOL: 
               - Advanced relevance scoring ensures high-quality matches
               - Automatically tries query variations if needed
               - Falls back to AI generation only when necessary
            
            ✅ EXCELLENT MULTI-KEYWORD QUERY EXAMPLES:
            - "artificial intelligence neural network visualization professional modern technology"
            - "data science team collaboration analytics modern office professional"
            - "cybersecurity professional monitoring dashboard security modern technology"
            - "cloud computing infrastructure diagram professional modern technology"
            - "agile development team planning meeting modern office professional"
            - "healthcare AI diagnosis medical technology doctor modern professional"
            - "financial technology trading analytics dashboard modern professional"
            
            ❌ POOR QUERY EXAMPLES (avoid these):
            - "technology" (too generic - needs 3-5 keywords)
            - "AI" (too vague - specify application domain)
            - "business cartoon" (avoid cartoon style)
            - "computer illustration" (prefer photorealistic)
            - "people working" (too generic - specify industry/context)
            
            🚨 MANDATORY REQUIREMENTS:
            - You MUST call unsplash_image_search for EACH image (the tool handles Unsplash vs AI intelligently)
            - Use 3-5 descriptive, specific keywords per query that match your content context
            - Always include domain context (healthcare, finance, education, etc.) when applicable
            - Copy the EXACT markdown returned by tools (including attribution)
            - Place images strategically to illustrate key points and break up text
            - NEVER create manual image URLs or skip tool calls
            - Focus on relevance - irrelevant images hurt user experience
            
            The enhanced tool now has intelligent query variation, semantic matching, and stricter 
            relevance filtering (60% threshold) to ensure you get the most relevant images.""",
            tools=tools,
            allow_delegation=False,
            llm=AgentFactory._create_llm(config.models.content_model),
        )

    @staticmethod
    def create_fact_checker(
        tools: List[Any], current_year: Optional[int] = None
    ) -> Agent:
        """Create a fact-checking agent for verifying content accuracy with live web validation."""
        year_context = (
            f" It is currently {current_year}, and you must ensure all information is up-to-date and relevant to this year."
            if current_year
            else ""
        )
        return Agent(
            role="Senior Fact Checker",
            goal="Verify the accuracy of claims and ensure content credibility",
            verbose=True,
            backstory=f"""You are a meticulous fact-checker with years of experience in
            journalism and content verification. Your sharp eye for detail and commitment to
            accuracy ensures that all published content meets the highest standards of
            credibility and reliability.{year_context}""",
            tools=tools,  # Provide web search tools for live source re-validation
            allow_delegation=False,
            llm=AgentFactory._create_llm(config.models.fact_check_model),
        )

    @staticmethod
    def create_finalizer(current_year: Optional[int] = None) -> Agent:
        """Create a finalization agent for polishing content."""
        year_context = (
            f" It is currently {current_year}, and you should ensure the final content reflects current industry standards and trends."
            if current_year
            else ""
        )
        return Agent(
            role="Editorial Finalizer",
            goal="Polish content to publication standards with perfect formatting",
            verbose=True,
            backstory=f"""You are an experienced editor who specializes in preparing content
            for publication. Your expertise lies in refining structure, improving readability,
            and ensuring consistent formatting. You have a keen eye for flow and always
            deliver content that engages readers from start to finish.{year_context}""",
            tools=[],
            allow_delegation=False,
            llm=AgentFactory._create_llm(config.models.finalization_model),
        )
