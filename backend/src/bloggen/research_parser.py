"""
Research Output Parser

Converts CrewAI research output (string) to structured StructuredResearchOutput object.
Handles various output formats including markdown-wrapped JSON.
"""

import json
import logging
import re
from typing import Optional
from .schemas.research_schema import StructuredResearchOutput

logger = logging.getLogger(__name__)


class ResearchOutputParser:
    """Parse and validate research agent output"""

    @staticmethod
    def parse_research_output(raw_output: str) -> Optional[StructuredResearchOutput]:
        """
        Parse research agent output string into structured object.

        Args:
            raw_output: Raw string output from research agent

        Returns:
            StructuredResearchOutput object or None if parsing fails
        """
        try:
            # Try to extract JSON from output (agent may wrap in markdown)
            json_str = ResearchOutputParser._extract_json(raw_output)

            if not json_str:
                logger.error("Failed to extract JSON from research output")
                logger.debug(f"Raw output preview: {raw_output[:500]}...")
                return None

            # Parse JSON
            research_data = json.loads(json_str)

            # Validate with Pydantic model
            structured_output = StructuredResearchOutput(**research_data)

            # Validate minimums
            is_valid, issues = structured_output.validate_minimums()

            if not is_valid:
                logger.error(
                    f"Research output failed minimum requirements: {issues}"
                )
                return None

            logger.info(
                f"✅ Parsed structured research: {structured_output.get_fact_count()} facts, "
                f"{structured_output.get_source_count()} sources"
            )
            return structured_output

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse research JSON: {e}")
            logger.debug(f"JSON string: {json_str[:500] if json_str else 'None'}...")
            return None
        except Exception as e:
            logger.error(f"Research parsing error: {e}")
            logger.debug(f"Raw output: {raw_output[:500]}...")
            return None

    @staticmethod
    def _extract_json(text: str) -> Optional[str]:
        """Extract JSON from text that may have markdown formatting"""
        if not text:
            return None

        text = text.strip()

        # Strategy 1: Look for markdown json code block
        json_block_pattern = r"```json\s*\n(.*?)\n```"
        matches = re.findall(json_block_pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()

        # Strategy 2: Look for generic code block
        code_block_pattern = r"```\s*\n(.*?)\n```"
        matches = re.findall(code_block_pattern, text, re.DOTALL)
        if matches:
            # Check if it looks like JSON
            for match in matches:
                if match.strip().startswith("{"):
                    return match.strip()

        # Strategy 3: Extract JSON object boundaries
        # Find first { and last } that could be JSON
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end > start:
            potential_json = text[start : end + 1]

            # Validate it's actually JSON-like
            if potential_json.count("{") > 0 and potential_json.count("}") > 0:
                return potential_json

        # Strategy 4: Try the whole text
        if text.startswith("{") and text.endswith("}"):
            return text

        logger.warning("Could not extract JSON from research output")
        return None

    @staticmethod
    def convert_to_dict(structured_research: StructuredResearchOutput) -> dict:
        """Convert structured research output to dictionary for serialization"""
        return structured_research.model_dump()

    @staticmethod
    def get_research_summary(
        structured_research: Optional[StructuredResearchOutput],
    ) -> str:
        """Generate a human-readable summary of research output"""
        if not structured_research:
            return "No structured research available"

        metrics = structured_research.get_quality_metrics()
        return f"""Research Summary:
- Topic: {structured_research.topic}
- Facts: {metrics['fact_count']}
- Statistics: {metrics['statistic_count']}
- Expert Quotes: {metrics['expert_quote_count']}
- Case Studies: {metrics['case_study_count']}
- Trends: {metrics['trend_count']}
- Unique Sources: {metrics['source_count']}
- Key Entities: {metrics['entity_count']}
"""
