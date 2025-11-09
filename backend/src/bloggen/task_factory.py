"""Task Factory for Blog Generation.

Creates specialized tasks for different phases of blog generation.
Follows Single Responsibility Principle - only creates and configures tasks.
"""

from crewai import Task, Agent
from typing import Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from .schemas.research_schema import StructuredResearchOutput

logger = logging.getLogger(__name__)


class TaskFactory:
    """Factory for creating specialized tasks for blog generation phases."""

    @staticmethod
    def create_research_task(
        agent: Agent, topic: str, current_year: int, instructions: Optional[str] = None
    ) -> Task:
        """Create a structured research task that outputs JSON format."""
        extra = (
            (
                "\n\nUSER DIRECTIVES (priority unless they conflict with sourcing rules):\n"
                + instructions.strip()
            )
            if instructions
            else ""
        )
        return Task(
            description=f"""🔍 MANDATORY DEEP RESEARCH TASK: Conduct comprehensive, in-depth research on '{topic}' with focus on {current_year} developments.

⚠️ CRITICAL TOOL USAGE REQUIREMENT:
You MUST actively use your web research tools (Serper search, web scraping) to gather CURRENT, DETAILED information.
This is NOT a task where you rely on training data. You MUST:
- Execute AT LEAST 5-7 different web searches with varied queries
- Search for: statistics, expert opinions, case studies, recent news, technical details
- Click through and read actual source content when tools provide URLs
- Gather SPECIFIC data: exact numbers, dates, company names, product versions, quotes
- Prioritize sources from {current_year} and {current_year - 1}

🚨 DEPTH REQUIREMENT: Your research summary alone must be 300-500 words of substantive content.
Each fact, statistic, and case study must be SPECIFIC and DETAILED with working source URLs.

🎯 OUTPUT FORMAT: You MUST return valid JSON matching this exact structure:

{{
  "topic": "{topic}",
  "summary": "300-500 word COMPREHENSIVE overview synthesizing ALL research findings - must demonstrate deep understanding and breadth of coverage",
  "key_entities": ["Entity1", "Entity2", "Entity3", "...at least 15 total"],
  "facts": [
    {{
      "statement": "SPECIFIC factual claim with exact details (50-200 chars) - e.g., 'OpenAI's GPT-4 achieved 89% accuracy on medical licensing exams in March 2024'",
      "source_url": "https://credible-source.com/article",
      "source_title": "Article Title",
      "confidence": "high",
      "year": {current_year},
      "category": "market data"
    }},
    "...minimum 20 facts total (not 15)"
  ],
  "statistics": [
    {{
      "metric_name": "Market Size",
      "value": "$184 billion (EXACT number required)",
      "context": "Global AI market in {current_year}, up 45% YoY from $127B in 2024",
      "source_url": "https://credible-source.com",
      "source_title": "Market Report Title",
      "year": {current_year}
    }},
    "...minimum 8 statistics total (not 5)"
  ],
  "expert_quotes": [
    {{
      "quote": "FULL direct quote from expert (50-300 chars) - e.g., 'The convergence of AI and quantum computing will fundamentally reshape how we approach problem-solving in the next decade'",
      "expert_name": "Dr. Jane Smith",
      "expert_title": "Chief AI Scientist at TechCorp",
      "source_url": "https://interview-source.com",
      "source_title": "Interview Title"
    }},
    "...minimum 3 quotes total (not 2)"
  ],
  "case_studies": [
    {{
      "company_or_project": "Company Name / Project Name",
      "description": "DETAILED description of what they did and how (100-400 chars) - include specific technologies, timeline, scale",
      "outcome": "MEASURABLE results achieved - include percentages, revenue impact, user growth, efficiency gains",
      "source_url": "https://case-study-source.com",
      "year": {current_year}
    }},
    "...minimum 3 case studies total (not 2)"
  ],
  "trends": [
    {{
      "trend_name": "Descriptive Trend Name (be specific, not generic)",
      "description": "DETAILED trend explanation (100-300 chars) - why it's happening, who's driving it, what's changing",
      "supporting_evidence": ["SPECIFIC evidence point 1 with data", "SPECIFIC evidence point 2 with data", "evidence point 3"],
      "source_urls": ["https://source1.com", "https://source2.com"]
    }},
    "...minimum 4 trends total (not 3)"
  ],
  "unique_sources": [
    {{
      "url": "https://source1.com",
      "title": "Source 1 Title",
      "credibility": "high"
    }},
    "...minimum 12 unique sources total (not 8)"
  ]
}}

🚨 MANDATORY MINIMUMS (Task fails if not met):
- **Summary**: 300-500 words of SUBSTANTIVE analysis (not generic overview)
- **Facts**: 20+ specific facts with sources and confidence levels (increased from 15)
- **Statistics**: 8+ statistics with EXACT values and detailed context (increased from 5)
- **Expert Quotes**: 3+ quotes with full attribution (increased from 2)
- **Case Studies**: 3+ case studies with MEASURABLE outcomes (increased from 2)
- **Trends**: 4+ identified trends with 3 supporting evidence points each (increased from 3)
- **Unique Sources**: 12+ credible sources (increased from 8)
- **Key Entities**: 15+ entities - tools, companies, technologies, products, platforms (increased from 10)

🔧 MANDATORY TOOL USAGE - YOU MUST:
1. Execute AT LEAST 5-7 web searches using your research tools
2. Search queries should cover:
   - "[topic] statistics {current_year}"
   - "[topic] market size {current_year}"
   - "[topic] case studies {current_year}"
   - "[topic] expert opinions {current_year}"
   - "[topic] trends {current_year}"
   - "[topic] companies products {current_year}"
   - "[topic] technical developments {current_year}"
3. Access actual web pages, don't rely on training data
4. Extract SPECIFIC information: exact numbers, dates, company names, versions
5. Verify source credibility and capture working URLs

RESEARCH REQUIREMENTS:
1. Use available web research tools (Serper search) for CURRENT {current_year} sources
2. Prioritize authoritative sources: official docs, research papers, reputable news, industry reports
3. Every fact/statistic MUST have a working source URL from actual web research
4. Prefer sources from {current_year} or {current_year - 1}
5. For each claim, capture: what (specific detail), when (exact date/timeframe), where (company/platform), source (working URL)
6. Avoid sources older than {current_year - 2} unless historically essential
7. **DEPTH OVER BREADTH**: Better to have 20 deeply researched, detailed facts than 50 shallow ones

QUALITY STANDARDS (CRITICAL - Your output will be validated):
- ❌ **UNACCEPTABLE**: "AI is growing rapidly" 
- ✅ **REQUIRED**: "The global AI market grew 45% YoY to reach $184 billion in {current_year}, driven primarily by enterprise adoption of large language models [Gartner Market Analysis, March {current_year}]"

- ❌ **UNACCEPTABLE**: Generic facts like "Company X is a leader in the field"
- ✅ **REQUIRED**: "Company X's Platform v3.2, released in February {current_year}, achieved 99.9% uptime and processed 50M daily transactions, a 300% increase from 2024 [Company X Technical Blog, Feb {current_year}]"

- Statistics MUST include: metric name, EXACT numeric value, units, context, comparison (YoY, vs competitors), year, source
- Expert quotes MUST include: COMPLETE quote text (not paraphrased), expert's full name, title, company/org, source URL
- Case studies MUST include: company name, specific technology/approach used, timeline, MEASURABLE results (%, $, user numbers), source
- Trends MUST have: clear description of what's changing, WHY it's happening, WHO is driving it, 3+ specific evidence points with data

{extra}

⚠️ VERIFICATION CHECKLIST - Before submitting, confirm:
- [ ] I used web research tools AT LEAST 5 times with different queries
- [ ] My summary is 300-500 words and demonstrates deep understanding
- [ ] I have 20+ facts with specific details (not generic statements)
- [ ] I have 8+ statistics with exact numbers (not "approximately" or "around")
- [ ] Every fact/statistic has a real source URL from my web research
- [ ] My case studies include specific measurable outcomes (percentages, revenue, growth numbers)
- [ ] Expert quotes are complete sentences, not paraphrases
- [ ] I named at least 15 specific entities (companies, products, tools, platforms)
- [ ] All sources are from {current_year} or {current_year - 1} (unless historically necessary)

⚠️ CRITICAL: Return ONLY valid JSON. No markdown formatting around JSON, no explanations outside JSON structure.
The JSON must be parseable by Python's json.loads(). Do not wrap in code blocks or add any text before/after the JSON.

🎯 RESEARCH DEPTH TARGET: Your research should provide enough material to support a 2000+ word blog post.
If your research feels thin or generic, you haven't researched deeply enough - go back and dig deeper with more specific searches.
""",
            agent=agent,
            expected_output="""Valid JSON object containing:
            - topic: string
            - summary: 300-500 chars COMPREHENSIVE overview with deep analysis
            - key_entities: array of 15+ specific entity names (companies, products, tools, platforms)
            - facts: array of 20+ detailed fact objects with working sources
            - statistics: array of 8+ statistic objects with exact numbers and context
            - expert_quotes: array of 3+ complete quote objects with full attribution
            - case_studies: array of 3+ case study objects with measurable outcomes
            - trends: array of 4+ trend objects with 3 supporting evidence points each
            - unique_sources: array of 12+ credible source objects from actual web research
            
            CRITICAL: Output must demonstrate ACTUAL web research (not training data).
            MUST be valid, parseable JSON with all required fields and INCREASED minimum counts met.
            Research must be SPECIFIC and DETAILED enough to support a 2000+ word blog post.""",
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
    def create_content_task_with_structured_research(
        agent: Agent,
        topic: str,
        current_year: int,
        structured_research: "StructuredResearchOutput",
        instructions: Optional[str] = None,
    ) -> Task:
        """Create enhanced content task with structured research context."""

        # Build research context summary from structured data
        research_summary = f"""
📊 AVAILABLE RESEARCH DATA (You MUST use this extensively):

🔢 KEY STATISTICS ({len(structured_research.statistics)} available - USE AT LEAST 3):
{chr(10).join(f"  • {s.metric_name}: {s.value} - {s.context} [{s.source_title}]" for s in structured_research.statistics[:8])}

💬 EXPERT QUOTES ({len(structured_research.expert_quotes)} available - USE AT LEAST 1):
{chr(10).join(f'  • "{q.quote}" - {q.expert_name}, {q.expert_title} [{q.source_title}]' for q in structured_research.expert_quotes)}

🏢 CASE STUDIES ({len(structured_research.case_studies)} available - USE AT LEAST 1):
{chr(10).join(f"  • {c.company_or_project}: {c.description} → {c.outcome} [{c.source_url}]" for c in structured_research.case_studies)}

📈 TRENDS ({len(structured_research.trends)} available - DISCUSS AT LEAST 2):
{chr(10).join(f"  • {t.trend_name}: {t.description}" for t in structured_research.trends)}

🔑 KEY ENTITIES TO MENTION ({len(structured_research.key_entities)} identified):
{', '.join(structured_research.key_entities[:25])}

📚 {len(structured_research.unique_sources)} CREDIBLE SOURCES available
All facts above have verified source URLs - use markdown links to cite them.
"""

        extra = (
            "\n\nUSER DIRECTIVES:\n" + instructions.strip() if instructions else ""
        )

        return Task(
            description=f"""Create a comprehensive, deeply researched blog post about '{topic}' for {current_year}.

{research_summary}

🎯 MANDATORY REQUIREMENTS:

1. **DEPTH & LENGTH:**
   - MINIMUM 1800 words (target 2000-2500)
   - MINIMUM 12 substantial paragraphs
   - MINIMUM 5 major sections with subsections

2. **USE RESEARCH DATA (MANDATORY):**
   - Include AT LEAST 10 specific facts from research
   - Reference AT LEAST 3 statistics with exact numbers
   - Include AT LEAST 1 expert quote
   - Mention AT LEAST 1 case study with outcomes
   - Discuss AT LEAST 2 identified trends with evidence
   - Mention AT LEAST 15 key entities by name (tools, companies, products)

3. **CITATIONS (MANDATORY):**
   - EVERY factual claim must have markdown link citation
   - Use format: [Descriptive text](source_url "source title")
   - MINIMUM 10 inline citations throughout content
   - NO vague claims like "studies show" without specific source

4. **STRUCTURE:**
   - Compelling title (60-80 characters, SEO-friendly)
   - Engaging introduction (200-250 words) with hook
   - 4-6 main sections, each 300-500 words minimum
   - Subsections for complex topics
   - Conclusion with actionable takeaways (150-200 words)

5. **SPECIFICITY (CRITICAL):**
   - Name specific tools, products, companies, versions
   - Include exact dates, numbers, percentages from research
   - Provide concrete examples, not generic statements
   - Technical details where relevant (from research data)

6. **IMAGES:**
   - Include 2-3 relevant images using tool calls
   - Place strategically to break up text

❌ PROHIBITED:
- Generic statements without specifics
- Vague references like "recent studies" without citation
- Superficial coverage of topics
- Sections shorter than 250 words
- Fewer than 1800 words total
- Making up data not in research

✅ QUALITY CHECKLIST:
- [ ] 1800+ words
- [ ] 10+ inline citations with real research URLs
- [ ] 3+ statistics with exact numbers from research
- [ ] 1+ expert quote from research
- [ ] 1+ case study example from research
- [ ] 15+ specific entities mentioned by name from research
- [ ] Every major claim has supporting evidence from research
- [ ] Technical depth appropriate for audience

{extra}

⚠️ REMEMBER: You have extensive structured research data above. Use it comprehensively. 
Readers expect deep, well-researched content with concrete examples and evidence.
Your research contains {len(structured_research.facts)} facts - use at least 10 of them!
""",
            agent=agent,
            expected_output="""A comprehensive, deeply researched blog post with:
            - 1800-2500 words of substantive content
            - 10+ inline citations to research sources
            - Specific facts, statistics, quotes, and case studies FROM RESEARCH
            - Named entities (tools, companies, products) FROM RESEARCH
            - Clear structure with 5+ major sections
            - Technical depth and actionable insights
            - Professional tone with engaging narrative
            - 2-3 strategically placed images
            - Final 'References' section with all sources
            
            Quality threshold: 7/10 minimum on content validator
            Research usage: Demonstrable use of provided structured research data""",
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
