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
    "...minimum 10-12 facts total"
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
    "...minimum 4-5 statistics total"
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
    "...minimum 6-8 unique sources total"
  ]
}}

🚨 MANDATORY MINIMUMS (Task fails if not met):
- **Summary**: 300-500 words of SUBSTANTIVE analysis (not generic overview)
- **Facts**: 10-12 specific facts with REAL working sources (focus on quality over quantity)
- **Statistics**: 4-5 statistics with EXACT values and detailed context
- **Expert Quotes**: 2-3 quotes with full attribution
- **Case Studies**: 2-3 case studies with MEASURABLE outcomes
- **Trends**: 3-4 identified trends with 3 supporting evidence points each
- **Unique Sources**: 6-8 credible sources from ACTUAL web research
- **Key Entities**: 10-15 entities - tools, companies, technologies, products, platforms

🔧 MANDATORY TOOL USAGE - YOU MUST:
1. Execute AT LEAST 5-7 web searches using your research tools
2. **ADAPT YOUR SEARCH STRATEGY** based on topic type:

   📚 **For HISTORICAL topics** (history of X, evolution of Y, ancient Z):
   - "[topic core concept]" (e.g., "ancient boat building techniques")
   - "[topic] archaeological evidence"
   - "[topic] historical development"
   - "[key time period] [topic]" (e.g., "Egyptian boats", "Phoenician ships")
   - "[topic] museum sources OR academic research"
   - "[topic] timeline OR chronology"
   - Only add "{current_year}" when searching for: "modern [topic]" OR "[topic] current state"

   🔬 **For MODERN/TECH topics** (AI, software, technology, business):
   - "[topic] statistics {current_year}"
   - "[topic] market size {current_year}"
   - "[topic] case studies {current_year}"
   - "[topic] expert opinions {current_year}"
   - "[topic] trends {current_year}"
   - "[topic] companies products {current_year}"
   - "[topic] technical developments {current_year}"

   🎨 **For GENERAL topics** (mix historical + modern):
   - Start with "[topic] overview" to understand scope
   - Then use 3-4 historical searches (background/origins)
   - Then use 2-3 modern searches (current state/future)

3. Access actual web pages, don't rely on training data
4. Extract SPECIFIC information: exact numbers, dates, company names, versions
5. Verify source credibility and capture working URLs

RESEARCH REQUIREMENTS:
1. Use available web research tools (Serper search) for CURRENT {current_year} sources
2. Prioritize authoritative sources: official docs, research papers, reputable news, industry reports
3. **CRITICAL**: ONLY include facts with REAL URLs from your actual web research - DO NOT fabricate URLs
4. **SOURCE SELECTION** - Adapt to topic type:
   - **Historical topics**: Wikipedia, Britannica, museum sites (.edu), archaeological journals, history publications
   - **Modern/Tech topics**: Company blogs, industry reports, news sites, official product docs
   - **Academic topics**: Research papers, university sites (.edu), peer-reviewed journals
5. For historical topics, sources from ANY year are acceptable if they contain factual historical information
6. For modern topics, prefer sources from {current_year} or {current_year - 1}
7. For each claim, capture: what (specific detail), when (exact date/timeframe), where (company/platform), source (working URL)
8. **QUALITY OVER QUANTITY**: Better to have 10 facts with REAL, working URLs than 20 with fake/hallucinated URLs
9. If your searches only return 6-8 credible sources, provide 10-12 facts from those sources - DO NOT invent additional URLs
10. **VERIFY BEFORE INCLUDING**: If you're not certain a URL exists, DON'T include it - use a different source

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
- [ ] I have 10-12 facts with specific details from REAL sources (not generic statements)
- [ ] I have 4-5 statistics with exact numbers (not "approximately" or "around")
- [ ] Every fact/statistic has a REAL source URL from my ACTUAL web research (no fabricated URLs)
- [ ] My case studies include specific measurable outcomes (percentages, revenue, growth numbers)
- [ ] Expert quotes are complete sentences, not paraphrases
- [ ] I named at least 10-15 specific entities (companies, products, tools, platforms)
- [ ] All sources are from {current_year} or {current_year - 1} (unless historically necessary)
- [ ] I did NOT make up URLs to meet quantity targets - all URLs are real

⚠️ CRITICAL: Return ONLY valid JSON. No markdown formatting around JSON, no explanations outside JSON structure.
The JSON must be parseable by Python's json.loads(). Do not wrap in code blocks or add any text before/after the JSON.

🎯 RESEARCH DEPTH TARGET: Your research should provide enough material to support a 2000+ word blog post.
If your research feels thin or generic, you haven't researched deeply enough - go back and dig deeper with more specific searches.
""",
            agent=agent,
            expected_output="""Valid JSON object containing:
            - topic: string
            - summary: 300-500 chars COMPREHENSIVE overview with deep analysis
            - key_entities: array of 10-15 specific entity names (companies, products, tools, platforms)
            - facts: array of 10-12 detailed fact objects with REAL working sources
            - statistics: array of 4-5 statistic objects with exact numbers and context
            - expert_quotes: array of 2-3 complete quote objects with full attribution
            - case_studies: array of 2-3 case study objects with measurable outcomes
            - trends: array of 3-4 trend objects with 3 supporting evidence points each
            - unique_sources: array of 6-8 credible source objects from ACTUAL web research
            
            CRITICAL: Output must demonstrate ACTUAL web research (not training data).
            ALL URLs must be REAL - DO NOT fabricate URLs to meet targets.
            MUST be valid, parseable JSON with all required fields and minimum counts met.
            Research must be SPECIFIC and DETAILED enough to support a 2000+ word blog post.""",
        )

    @staticmethod
    def create_content_task(
        agent: Agent, topic: str, current_year: int, instructions: Optional[str] = None
    ) -> Task:
        """Create a content creation task for writing blog posts with emphasis on depth and length."""
        extra = (
            (
                "\n\nUSER DIRECTIVES (priority unless they conflict with factual accuracy / sourcing):\n"
                + instructions.strip()
            )
            if instructions
            else ""
        )
        return Task(
            description=f"""📝 COMPREHENSIVE BLOG WRITING TASK: Create a detailed, in-depth blog post about '{topic}' for {current_year}.

🧠 BEFORE YOU BEGIN - ANSWER THESE QUESTIONS TO YOURSELF:
1. What is my PRIMARY objective? (Answer: Write 1800-2500 words of content)
2. What is my MINIMUM word count target? (Answer: 1800 words)
3. How many major sections do I need? (Answer: 5-7 sections of 200-350 words each)
4. When should I add images? (Answer: ONLY after completing ALL 1800+ words)
5. How many citations do I need? (Answer: Minimum 5-7 citations in [text](url) format)
6. What happens if I stop early? (Answer: Content will FAIL validation and waste time)

Now that you've acknowledged these requirements, proceed with writing.

🎯 PRIMARY OBJECTIVE: WRITE AT LEAST 1800-2500 WORDS OF SUBSTANTIVE CONTENT

⚠️ CRITICAL LENGTH REQUIREMENT:
Your blog post MUST be between 1800-2500 words (NOT including references).
- Minimum acceptable: 1800 words
- Target range: 2000-2200 words  
- Maximum: 2500 words
- Word count is PRIORITY #1 - without sufficient length, all other requirements are irrelevant

🚨 ABSOLUTE RULE: DO NOT STOP WRITING TO INSERT IMAGES UNTIL YOU COMPLETE ALL 1800+ WORDS
- Write ALL sections completely FIRST
- Reach the full word count BEFORE using any image tools
- Images are SECONDARY - add them ONLY after content is complete
- If you stop early to add images, your content will FAIL validation

📊 CONTENT STRUCTURE REQUIREMENTS (ALL MANDATORY):

1. **COMPELLING TITLE** (10-15 words)
   - SEO-optimized and attention-grabbing
   - Include primary keyword naturally

2. **ENGAGING INTRODUCTION** (200-300 words)
   - Hook the reader with a compelling question, statistic, or story
   - Clearly state what the article covers
   - Explain why the topic matters in {current_year}
   - Provide a brief roadmap of sections

3. **MAIN CONTENT SECTIONS** (1400-1800 words total across 5-7 sections)
   - Each section should be 200-350 words
   - Use descriptive H2 headers (##) for main sections
   - Use H3 headers (###) for subsections where appropriate
   - Each section must provide DEPTH, not just breadth
   - Include specific examples, data points, and explanations
   - Don't just list concepts - EXPLAIN them thoroughly
   
   Example sections structure:
   - ## Understanding [Core Concept] (250-300 words)
   - ## Current State of [Topic] in {current_year} (300-350 words)
   - ## Key Technologies/Approaches (300-350 words)
   - ## Real-World Applications (250-300 words)
   - ## Challenges and Limitations (200-250 words)
   - ## Future Outlook (200-250 words)
   - ## Best Practices/Recommendations (200-250 words)

4. **CONCLUSION** (150-200 words)
   - Synthesize key takeaways
   - Provide actionable next steps
   - End with a forward-looking statement

5. **REFERENCES SECTION**
   - Numbered list of all sources cited
   - Format: "1. Source Title. URL"

💡 WRITING QUALITY STANDARDS:

**DEPTH OVER BREADTH**: 
- ❌ BAD: "AI is transforming healthcare through various applications."
- ✅ GOOD: "AI is transforming healthcare through applications like diagnostic imaging analysis, where deep learning models can detect lung nodules with 94% accuracy compared to 88% for radiologists alone. IBM's Watson Health processed over 200 million patient records in 2024, identifying treatment patterns that reduced hospital readmission rates by 23% across participating institutions."

**SPECIFIC EXAMPLES**:
- Every major point should have a concrete example
- Include company names, product versions, specific numbers
- Reference real implementations and case studies

**PARAGRAPH STRUCTURE**:
- Each paragraph should be 4-6 sentences (80-120 words)
- Start with a clear topic sentence
- Provide supporting details and examples
- End with a transition or summary

**EXPLANATORY DEPTH**:
- Don't assume reader knowledge - explain concepts
- Use analogies when helpful
- Break down complex ideas into digestible parts

**CITATION FORMAT (CRITICAL - Citations often get stripped accidentally)**:
- ALWAYS use markdown link format: [descriptive text](https://url.com)
- Place citations at end of sentences that need sourcing
- DO NOT remove or strip citation links during writing
- Example: "The market grew 45% in 2024 [according to Gartner](https://example.com/report)."
- Every statistic, claim, or data point MUST have a citation
- Aim for AT LEAST 5-7 citations throughout the article

📸 IMAGE REQUIREMENTS (SECONDARY PRIORITY - DO THIS LAST):

⚠️ ONLY ADD IMAGES AFTER YOU COMPLETE ALL 1800+ WORDS OF CONTENT

🚨 CRITICAL IMAGE RULES - READ CAREFULLY:
- **DO NOT write image markdown yourself** - you MUST use the unsplash_image_search tool
- **DO NOT fabricate Unsplash URLs** - the tool will provide real, working URLs
- **DO NOT copy old Unsplash URL patterns** - they are deprecated and will fail
- If you write `![...](https://images.unsplash.com/...)` WITHOUT using the tool, the image WILL BE BROKEN

After writing your comprehensive content, enhance it with 2-3 images by CALLING THE TOOL:

1. **First Image** (after introduction):
   - MUST CALL TOOL: unsplash_image_search("{{topic}} professional modern technology")
   - DO NOT write image markdown manually - let the tool generate it
   - Place the tool's output immediately after introduction paragraph

2. **Second Image** (middle section):
   - MUST CALL TOOL: unsplash_image_search("{{topic}} application example")
   - DO NOT write image markdown manually - let the tool generate it
   - Place the tool's output in the middle of main content

3. **Optional Third Image** (if content >2000 words):
   - MUST CALL TOOL: unsplash_image_search("{{topic}} future innovation")
   - DO NOT write image markdown manually - let the tool generate it
   - Place the tool's output near conclusion

**WHY YOU MUST USE THE TOOL:**
- The tool validates URLs are real and working
- The tool includes proper photographer attribution
- Manually written URLs are almost always broken (404 errors)
- Your generated URLs use deprecated formats that no longer work

🔗 SOURCING AND CITATIONS:

- Preserve inline source links throughout: [1], [2], etc.
- Every major claim should reference a source
- Include at least 8-10 different sources in References section

✍️ TONE AND STYLE:

- Professional yet conversational
- Use "you" to engage readers
- Vary sentence length for readability
- Use transitional phrases between sections
- Active voice preferred over passive

{extra}

⚠️ VALIDATION CHECKLIST (Verify before submitting):

□ My blog post is 1800-2500 words (excluding references)
□ I have 5-7 main content sections with H2 headers
□ Each section is 200-350 words with substantive content
□ I included specific examples with company names and data
□ Introduction is 200-300 words with clear hook
□ Conclusion is 150-200 words with actionable takeaways
□ I called image tools 2-3 times and included the returned markdown
□ I have a properly formatted References section
□ Every paragraph provides depth, not just surface-level information

🚨 CRITICAL: If your content is under 1800 words, STOP and add more depth to existing sections.
Do NOT submit short content - it will be rejected. Focus on EXPLAINING concepts thoroughly.""",
            agent=agent,
            expected_output="""A comprehensive blog post meeting ALL requirements:
            
            LENGTH: 1800-2500 words of substantive content (NOT including references)
            
            STRUCTURE:
            - Compelling SEO-optimized title (10-15 words)
            - Engaging introduction (200-300 words) with hook and roadmap
            - 5-7 well-developed main content sections with H2 headers
            - Each section: 200-350 words with depth and specific examples
            - Thoughtful conclusion (150-200 words) with takeaways
            - Properly formatted References section with 8-10+ sources
            
            IMAGES:
            - 2-3 relevant images from tool calls (unsplash_image_search)
            - Proper markdown formatting with attribution
            - Strategic placement throughout content
            
            QUALITY:
            - Specific examples with company names, data, and details
            - Clear explanations of complex concepts
            - Professional yet conversational tone
            - Natural keyword integration
            - Inline source citations [1], [2], etc.
            
            🚨 MANDATORY: Content MUST be 1800+ words. Shorter content will be rejected and require rewrite.""",
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
