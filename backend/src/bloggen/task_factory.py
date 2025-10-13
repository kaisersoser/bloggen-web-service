"""Task Factory for Blog Generation.

Creates specialized tasks for different phases of blog generation.
Follows Single Responsibility Principle - only creates and configures tasks.
"""

from crewai import Task, Agent
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TaskFactory:
    """Factory for creating specialized tasks for blog generation phases."""

    @staticmethod
    def create_research_task(
        agent: Agent, topic: str, current_year: int, instructions: Optional[str] = None
    ) -> Task:
        """Create a research task for gathering information on a topic."""
        extra = (
            (
                "\n\nUSER DIRECTIVES (priority unless they conflict with sourcing rules):\n"
                + instructions.strip()
            )
            if instructions
            else ""
        )
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
            - 'Sources' section: numbered markdown list of unique source URLs used above""",
        )

    @staticmethod
    def create_content_task(
        agent: Agent, topic: str, current_year: int, instructions: Optional[str] = None
    ) -> Task:
        """Create a content creation task for writing blog posts with mandatory image enforcement."""
        extra = (
            (
                "\n\nUSER DIRECTIVES (priority unless they conflict with factual accuracy / sourcing):\n"
                + instructions.strip()
            )
            if instructions
            else ""
        )
        return Task(
            description=f"""🚨 MANDATORY TOOL USAGE TASK: Create an engaging blog post about '{topic}' for {current_year}.
            
            ⚠️ CRITICAL IMAGE REQUIREMENT: This task REQUIRES you to call image tools 2-3 times. Follow this EXACT workflow:
            
            STEP 1: Write compelling introduction paragraph
            STEP 2: 🔧 CALL unsplash_image_search("{{topic}} hero visual concept")
            STEP 3: Insert the returned image markdown immediately after introduction
            STEP 4: Write main content sections (2-3 sections minimum)
            STEP 5: 🔧 CALL unsplash_image_search("{{topic}} supporting visual")
            STEP 6: Insert the second image markdown in the middle section
            STEP 7: Continue writing remaining content sections
            STEP 8: 🔧 CALL openai_image_generate("{{topic}} illustration concept") for third image
            STEP 9: Insert third image if content is substantial (1500+ words)
            
            🚨 IMAGE ENFORCEMENT - FOLLOW EXACTLY:
            - MINIMUM 2 IMAGES REQUIRED (preferably 3 for blogs >1500 words)
            - FIRST IMAGE: Use unsplash_image_search with descriptive multi-word query
            - SECOND IMAGE: Use unsplash_image_search with different supporting concept
            - THIRD IMAGE (optional): Use openai_image_generate for illustration/diagram
            - NEVER create fake image URLs (no source.unsplash.com, no manual links)
            - ONLY use images returned by actual tool calls
            - If Unsplash returns no results, immediately try openai_image_generate as fallback
            
            ❌ PROHIBITED ACTIONS:
            - Creating manual image URLs
            - Using placeholder image services
            - Skipping image tool calls
            - Including fewer than 2 images
            
            ✅ REQUIRED ACTIONS:
            - Call unsplash_image_search at least twice with different queries
            - Use openai_image_generate if Unsplash fails or for third image
            - Include ALL returned image markdown blocks in appropriate locations
            - Ensure each image has proper attribution and alt text
            
            Content Requirements:
            1. Title: Compelling and SEO-friendly
            2. Structure: Clear headers and subheadings (minimum 4-5 sections)
            3. Content: Informative, engaging, and actionable (1500-2000 words)
            4. SEO: Natural keyword integration throughout
            5. IMAGES: EXACTLY 2-3 images using MANDATORY tool calls (as detailed above)
            6. Tone: Professional yet conversational
            7. SOURCING: Preserve all validated source links from research
            8. REFERENCES: End with numbered 'References' section
            9. Place first image after introduction, others distributed through content
            10. Do NOT put images inside code blocks or lists
            
            🚨 FAILURE TO CALL IMAGE TOOLS 2-3 TIMES WILL RESULT IN TASK REJECTION{extra}
            """,
            agent=agent,
            expected_output="""A complete blog post with MANDATORY TOOL USAGE COMPLIANCE:
            - SEO-optimized title and compelling introduction
            - Well-structured content with clear headers (4-5 sections minimum)
            - EXACTLY 2-3 IMAGES from verified tool calls (unsplash_image_search/openai_image_generate)
            - First image: Hero image after introduction (from unsplash_image_search)
            - Second image: Supporting image in middle content (from unsplash_image_search)
            - Third image (if applicable): Illustration/diagram (from openai_image_generate)
            - ALL images must have proper markdown formatting and attribution
            - Actionable insights and examples with inline source links
            - Natural keyword integration throughout content
            - Final 'References' section with numbered, unique sources
            
            🚨 CRITICAL: Output MUST contain 2-3 actual images from tool calls. No manual URLs allowed.
            🚨 CRITICAL: Use only tool-generated image markdown blocks, never create fake URLs.
            🚨 CRITICAL: If fewer than 2 images included, task will be considered FAILED.""",
        )

    @staticmethod
    def create_fact_check_task(
        agent: Agent, topic: str, instructions: Optional[str] = None
    ) -> Task:
        """Create a fact-checking task for verifying content accuracy with mandatory URL validation."""
        extra = (
            (
                "\n\nUSER ORIGINAL DIRECTIVES (retain intent while enforcing verification):\n"
                + instructions.strip()
            )
            if instructions
            else ""
        )
        return Task(
            description=f"""Thoroughly fact-check the blog post about '{topic}' with MANDATORY URL validation.

            🔍 URL VALIDATION REQUIREMENT (CRITICAL):
            BEFORE providing final output, you MUST use the URLValidationTool or BulkURLValidationTool to test EVERY link in the content:
            - Test each URL to verify it returns HTTP 200 (accessible)
            - Replace any broken links (404, timeout, SSL errors) with working alternatives
            - For broken links: search for current working sources on the same topic
            - Document all URL changes in your fact-check summary

            LIVE RE-VALIDATION (MANDATORY): Use the provided web research/search tool(s) to re-check every statistic, date, numeric metric, market figure, quote, and technical claim.
            For each claim:
              - Confirm the link is still valid and authoritative using URL validation tools
              - Replace broken / low-credibility sources with better ones
              - Add missing links where claims lack sourcing (search for them; if no credible source found, mark the claim UNSOURCED and recommend removal or rewrite)

            Verification process:
            1. Re-verify all statistical claims (ensure numbers & units match current context)
            2. Confirm examples & case studies still accurate / up to date
            3. Validate technical terminology and version references
            4. **VALIDATE ALL URLS**: Use URL validation tools to test every link before final output
            5. Ensure EVERY factual sentence has an inline markdown link (except clearly marked opinion / synthesis)
            6. Flag outdated (>2 years) data unless historically framed
            7. Provide a concise correction log summarizing changes including URL fixes

            Output MUST keep existing structure but update references accordingly.{extra}
            """,
            agent=agent,
            expected_output="""A fact-checked version with:
            - All factual claims verified with current sources
            - ALL URLs validated and working (no 404s, timeouts, or broken links)
            - Added / updated inline links where missing or weak
            - Outdated or unsourced claims flagged or revised
            - Consolidated, deduplicated 'References' section (numbered)
            - A 'Fact Check Summary' section listing corrections, replaced sources, and URL validation results
            - 'URL Validation Report' showing tested links and any replacements made""",
        )

    @staticmethod
    def create_finalization_task(
        agent: Agent, topic: str, instructions: Optional[str] = None
    ) -> Task:
        """Create a finalization task for polishing content."""
        extra = (
            (
                "\n\nUSER DIRECTIVES (final polish should respect these preferences):\n"
                + instructions.strip()
            )
            if instructions
            else ""
        )
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
            11. IMAGE PRESERVATION: Keep all inserted Unsplash image markdown blocks. Improve alt text only if it becomes clearer (retain attribution lines). Do NOT delete images unless they are clear duplicates.
            12. Ensure first image placement remains after opening context; adjust spacing if needed (one blank line before & after).
            
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
            - Final 'References' section (numbered, unique, valid URLs)""",
        )

    @staticmethod
    def create_image_enhancement_task(agent: Agent, content: str, topic: str) -> Task:
        """Create a task to add missing images to existing content."""
        return Task(
            description=f"""🎨 IMAGE ENHANCEMENT: Add missing images to existing blog content about '{topic}'.
            
            CRITICAL: The provided content may be missing adequate images. Your task is to:
            
            1. Review the existing content structure and identify optimal image placement
            2. CALL unsplash_image_search to find 1-2 relevant images for the content
            3. Insert the returned image markdown blocks in appropriate locations
            4. Ensure images enhance the content and match the topic theme
            5. Do NOT modify the existing text content - only add images
            
            IMAGE REQUIREMENTS:
            - Use descriptive, multi-word queries for unsplash_image_search
            - Insert images between sections where they add value
            - Include proper alt text and attribution
            - Do NOT create manual image URLs or placeholders
            
            Return the enhanced content with properly formatted image markdown blocks added.""",
            agent=agent,
            expected_output="""Enhanced content with:
            - Original text content preserved
            - 1-2 new images from unsplash_image_search tool calls
            - Images placed strategically between content sections
            - Proper markdown formatting for all images
            - Alt text and attribution maintained""",
        )
