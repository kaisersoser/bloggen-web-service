"""
Structured Research Output Schema

Enforces research agents to produce queryable, structured data
instead of unstructured text blobs. This enables better quality
control and makes research findings easily accessible to content
generation agents.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


class ResearchFact(BaseModel):
    """Single verifiable fact with source attribution"""

    statement: str = Field(..., min_length=20, max_length=500)
    source_url: HttpUrl
    source_title: str
    confidence: str = Field(..., pattern="^(high|medium|low)$")
    year: Optional[int] = None
    category: str = ""  # e.g., "statistics", "expert opinion", "case study"


class ResearchStatistic(BaseModel):
    """Quantitative data point with source"""

    metric_name: str
    value: str  # e.g., "45%", "$2.3B", "3x faster"
    context: str  # What it measures
    source_url: HttpUrl
    source_title: str
    year: int


class ExpertQuote(BaseModel):
    """Direct quote from subject matter expert"""

    quote: str = Field(..., min_length=30, max_length=300)
    expert_name: str
    expert_title: str
    source_url: HttpUrl
    source_title: str


class CaseStudy(BaseModel):
    """Real-world implementation example"""

    company_or_project: str
    description: str = Field(..., min_length=50, max_length=400)
    outcome: str
    source_url: HttpUrl
    year: Optional[int] = None


class ResearchTrend(BaseModel):
    """Identified industry trend with supporting evidence"""

    trend_name: str
    description: str = Field(..., min_length=50, max_length=300)
    supporting_evidence: List[str] = Field(..., min_length=2)
    source_urls: List[HttpUrl] = Field(..., min_length=1)


class StructuredResearchOutput(BaseModel):
    """Complete structured research output with enforced minimums"""

    # Overview
    topic: str
    summary: str = Field(..., min_length=150, max_length=500)
    research_timestamp: datetime = Field(default_factory=datetime.now)

    # Key entities mentioned (tools, companies, technologies)
    key_entities: List[str] = Field(..., min_length=10, max_length=50)

    # Structured data (with MINIMUMS - reduced to realistic levels)
    facts: List[ResearchFact] = Field(..., min_length=10)
    statistics: List[ResearchStatistic] = Field(..., min_length=4)
    expert_quotes: List[ExpertQuote] = Field(..., min_length=2)
    case_studies: List[CaseStudy] = Field(..., min_length=2)
    trends: List[ResearchTrend] = Field(..., min_length=3)

    # Source tracking
    unique_sources: List[Dict[str, str]] = Field(..., min_length=6)
    # Format: [{"url": "https://...", "title": "...", "credibility": "high/medium"}]

    def get_fact_count(self) -> int:
        """Get total number of facts"""
        return len(self.facts)

    def get_source_count(self) -> int:
        """Get total number of unique sources"""
        return len(self.unique_sources)

    def validate_minimums(self) -> tuple[bool, List[str]]:
        """Check if output meets minimum requirements"""
        issues = []

        if len(self.facts) < 10:
            issues.append(f"Insufficient facts: {len(self.facts)}/10 minimum")
        if len(self.statistics) < 4:
            issues.append(
                f"Insufficient statistics: {len(self.statistics)}/4 minimum"
            )
        if len(self.expert_quotes) < 2:
            issues.append(
                f"Insufficient expert quotes: {len(self.expert_quotes)}/2 minimum"
            )
        if len(self.case_studies) < 2:
            issues.append(
                f"Insufficient case studies: {len(self.case_studies)}/2 minimum"
            )
        if len(self.trends) < 3:
            issues.append(f"Insufficient trends: {len(self.trends)}/3 minimum")
        if len(self.unique_sources) < 6:
            issues.append(
                f"Insufficient sources: {len(self.unique_sources)}/6 minimum"
            )
        if len(self.key_entities) < 10:
            issues.append(
                f"Insufficient key entities: {len(self.key_entities)}/10 minimum"
            )

        return len(issues) == 0, issues

    def get_quality_metrics(self) -> Dict[str, int]:
        """Get comprehensive quality metrics"""
        return {
            "fact_count": len(self.facts),
            "statistic_count": len(self.statistics),
            "source_count": len(self.unique_sources),
            "entity_count": len(self.key_entities),
            "expert_quote_count": len(self.expert_quotes),
            "case_study_count": len(self.case_studies),
            "trend_count": len(self.trends),
        }
