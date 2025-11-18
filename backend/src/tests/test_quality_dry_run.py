#!/usr/bin/env python3
"""
Quick Quality Test - Dry Run

Tests the quality improvement system without actually calling AI APIs.
Validates all components work together correctly.

Usage:
    cd backend
    source .venv/bin/activate
    python test_quality_dry_run.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from bloggen.schemas.research_schema import (
    StructuredResearchOutput,
    ResearchFact,
    ResearchStatistic,
    ExpertQuote,
    CaseStudy,
    ResearchTrend,
)
from bloggen.research_parser import ResearchOutputParser
from bloggen.quality_validator import QualityValidator
from bloggen.task_factory import TaskFactory
from crewai import Agent


def create_mock_research_data():
    """Create mock research data for testing."""
    return {
        "topic": "GraphQL vs REST APIs in 2025",
        "summary": "Comprehensive comparison of GraphQL and REST API architectures, examining performance, developer experience, ecosystem maturity, and real-world adoption patterns in modern web development.",
        "key_entities": [
            "GraphQL", "REST", "Apollo", "Relay", "Netflix", "GitHub",
            "Express", "FastAPI", "Prisma", "Hasura", "PostgreSQL", "MongoDB"
        ],
        "facts": [
            {
                "statement": "GraphQL was developed by Facebook in 2012 and open-sourced in 2015",
                "source_url": "https://graphql.org/foundation/",
                "source_title": "GraphQL Foundation",
                "confidence": "high",
                "year": 2015,
                "category": "history"
            }
        ] * 15,  # 15 facts
        "statistics": [
            {
                "metric_name": "GraphQL Adoption Rate",
                "value": "38%",
                "context": "Percentage of companies using GraphQL in production",
                "source_url": "https://survey.example.com/2024",
                "source_title": "State of APIs Survey 2024",
                "year": 2024
            }
        ] * 5,  # 5 statistics
        "expert_quotes": [
            {
                "quote": "GraphQL gives clients the power to ask for exactly what they need",
                "expert_name": "Lee Byron",
                "expert_title": "GraphQL Co-Creator",
                "source_url": "https://example.com/interview",
                "source_title": "GraphQL Origins Interview"
            }
        ] * 2,  # 2 quotes
        "case_studies": [
            {
                "company_or_project": "GitHub",
                "description": "Migrated API v4 to GraphQL, enabling more efficient data fetching for developers",
                "outcome": "Reduced API calls by 40% while improving developer satisfaction",
                "source_url": "https://github.blog/graphql",
                "year": 2022
            }
        ] * 2,  # 2 case studies
        "trends": [
            {
                "trend_name": "Unified Data Layer Adoption",
                "description": "Companies moving to GraphQL as unified API layer across microservices",
                "supporting_evidence": [
                    "Netflix using GraphQL federation",
                    "PayPal consolidated 10+ REST endpoints into single GraphQL API"
                ],
                "source_urls": ["https://example.com/trends"]
            }
        ] * 3,  # 3 trends
        "unique_sources": [
            {"url": f"https://source{i}.com", "title": f"Source {i}", "credibility": "high"}
            for i in range(8)
        ]
    }


def test_research_parsing():
    """Test research parsing and validation."""
    print("\n" + "="*80)
    print("TEST 1: Research Parsing & Validation")
    print("="*80)
    
    # Create mock data
    mock_data = create_mock_research_data()
    json_output = json.dumps(mock_data)
    
    # Test parsing
    print("\n📝 Parsing research output...")
    research = ResearchOutputParser.parse_research_output(json_output)
    
    if research:
        print("   ✅ Parsing successful")
        print(f"   - Facts: {research.get_fact_count()}")
        print(f"   - Statistics: {len(research.statistics)}")
        print(f"   - Expert Quotes: {len(research.expert_quotes)}")
        print(f"   - Case Studies: {len(research.case_studies)}")
        print(f"   - Trends: {len(research.trends)}")
        print(f"   - Sources: {research.get_source_count()}")
    else:
        print("   ❌ Parsing failed")
        return (False, None)
    
    # Test validation
    print("\n✅ Validating research quality...")
    is_valid, issues, metrics = QualityValidator.validate_research_quality(research)
    
    print(f"   Valid: {is_valid}")
    print(f"   Issues: {len(issues)}")
    
    if issues:
        for issue in issues:
            print(f"   - {issue}")
    
    print(f"\n📊 Metrics:")
    for key, value in metrics.items():
        print(f"   {key}: {value}")
    
    return (is_valid, research)


def test_enhanced_task_creation(research):
    """Test enhanced content task creation."""
    print("\n" + "="*80)
    print("TEST 2: Enhanced Content Task Creation")
    print("="*80)
    
    print("\n🏗️  Creating enhanced content task...")
    
    factory = TaskFactory()
    agent = Agent(
        role="Content Creator",
        goal="Create blog content",
        backstory="Expert technical writer"
    )
    
    task = factory.create_content_task_with_structured_research(
        agent=agent,
        topic="GraphQL vs REST APIs",
        current_year=2025,
        structured_research=research,
        instructions="Focus on practical examples"
    )
    
    print("   ✅ Task created successfully")
    print(f"   Task description length: {len(task.description)} characters")
    
    # Verify research data is in task
    checks = {
        "AVAILABLE RESEARCH DATA": "Research context header",
        "KEY STATISTICS": "Statistics section",
        "EXPERT QUOTES": "Quotes section",
        "CASE STUDIES": "Case studies section",
        "TRENDS": "Trends section",
        "1800 words": "Word count requirement",
        "10+ inline citations": "Citation requirement"
    }
    
    print("\n📋 Task Content Verification:")
    all_present = True
    for check, description in checks.items():
        if check in task.description:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description} - MISSING!")
            all_present = False
    
    return all_present


def test_content_validation():
    """Test content validation with sample blog."""
    print("\n" + "="*80)
    print("TEST 3: Content Quality Validation")
    print("="*80)
    
    # Sample high-quality content
    good_content = """# GraphQL vs REST APIs: A Comprehensive Comparison for 2025

## Introduction

The API landscape has evolved significantly over the past decade, with [GraphQL emerging](https://graphql.org "GraphQL Official Site") as a powerful alternative to traditional REST architectures. According to the [State of APIs Survey 2024](https://survey.example.com "API Survey"), 38% of companies now use GraphQL in production, marking a significant shift in how developers approach API design.

As [Lee Byron, GraphQL co-creator, notes](https://example.com "GraphQL Origins"): "GraphQL gives clients the power to ask for exactly what they need," highlighting one of the key advantages over REST's fixed endpoint structure. This flexibility has driven adoption across major tech companies, with [GitHub successfully migrating](https://github.blog "GitHub Engineering") their API v4 to GraphQL, resulting in a 40% reduction in API calls.

## Performance and Efficiency

GraphQL's query language allows clients to request exactly the data they need, eliminating over-fetching and under-fetching problems common in REST APIs. [Netflix implemented GraphQL federation](https://netflix.tech "Netflix Tech Blog"), enabling them to unify data across microservices while maintaining high performance. The result was a [15% improvement in API response times](https://benchmark.example.com "API Benchmarks") and better developer productivity.

REST APIs, while simpler in concept, often require multiple round trips to fetch related data. However, REST benefits from widespread HTTP caching mechanisms and [CDN optimization strategies](https://cloudflare.com "Cloudflare Docs") that are well-understood and battle-tested. For simple CRUD operations, [REST remains 20% faster](https://performance.example.com "Performance Study") due to lower parsing overhead.

## Developer Experience

The developer experience differs significantly between the two approaches. GraphQL's [strong typing system](https://spec.graphql.org "GraphQL Spec") and introspection capabilities enable powerful tooling like [GraphiQL](https://github.com/graphql/graphiql "GraphiQL Repository") and automatic documentation generation. [PayPal consolidated 10+ REST endpoints](https://paypal.engineering "PayPal Engineering") into a single GraphQL API, dramatically simplifying their frontend codebase.

REST's simplicity and stateless nature make it easier for beginners to understand. The [OpenAPI specification](https://openapis.org "OpenAPI Initiative") provides excellent documentation capabilities, and REST's alignment with HTTP semantics makes caching strategies straightforward. However, maintaining multiple endpoints as applications grow can become [30% more time-consuming](https://productivity.example.com "Developer Productivity Report") compared to GraphQL's unified schema.

## Ecosystem and Tooling

The GraphQL ecosystem has matured rapidly, with robust implementations in [Apollo Client](https://apollographql.com "Apollo GraphQL"), [Relay](https://relay.dev "Relay Framework"), and [Prisma](https://prisma.io "Prisma ORM"). [Hasura](https://hasura.io "Hasura GraphQL Engine") enables instant GraphQL APIs over PostgreSQL and other databases, reducing development time by [50% in many cases](https://hasura.blog "Hasura Blog").

REST benefits from decades of tooling maturity. Frameworks like [Express.js](https://expressjs.com "Express Framework"), [FastAPI](https://fastapi.tiangolo.com "FastAPI Framework"), and [Django REST Framework](https://django-rest-framework.org "Django REST") provide comprehensive solutions. HTTP libraries in every programming language offer first-class REST support, and [rate limiting](https://ratelimit.example.com "Rate Limiting Guide") and authentication patterns are well-established.

## Real-World Adoption Patterns

Major companies have adopted both approaches based on their specific needs. [GitHub uses GraphQL](https://github.blog "GitHub API v4") for their public API v4, while maintaining REST for backwards compatibility. [Twitter's API v2](https://developer.twitter.com "Twitter Developer") sticks with REST but incorporates field selection to address over-fetching issues.

The trend toward [unified data layers](https://datalayer.example.com "Unified Data Architecture") is driving GraphQL adoption, especially in companies with complex microservice architectures. [70% of Fortune 500 companies](https://enterprise.survey.com "Enterprise Technology Survey") evaluating new API strategies are considering GraphQL for internal APIs, though REST remains dominant for public-facing APIs.

## Conclusion

Both GraphQL and REST have their place in modern API design. GraphQL excels in complex applications with diverse client needs, offering flexibility and efficiency. REST remains the pragmatic choice for simple APIs, public endpoints, and scenarios requiring extensive caching. The decision should be based on specific project requirements, team expertise, and long-term maintenance considerations.

As we move through 2025, the API landscape continues to evolve, with both approaches learning from each other. [Federation patterns](https://federation.example.com "API Federation") and [schema stitching](https://stitching.example.com "Schema Stitching") in GraphQL, combined with REST's simplicity and caching strengths, are shaping the future of API design.
"""
    
    print("\n📝 Validating high-quality content...")
    # Use lower thresholds for testing (sample content is ~616 words)
    is_valid, issues, metrics = QualityValidator.validate_content_quality(
        good_content,
        min_words=500,
        min_paragraphs=5,
        min_sections=4,
        min_citations=10
    )
    
    print(f"   Valid: {is_valid}")
    print(f"   Word Count: {metrics['word_count']}")
    print(f"   Citations: {metrics['citation_count']}")
    print(f"   Sections: {metrics['section_count']}")
    print(f"   Issues: {len(issues)}")
    
    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"   - {issue}")
    else:
        print("\n✅ No issues - content meets quality standards!")
    
    # Test low-quality content
    print("\n📝 Testing detection of low-quality content...")
    bad_content = "This is a very short blog with no citations or structure."
    
    is_valid_bad, issues_bad, metrics_bad = QualityValidator.validate_content_quality(bad_content)
    print(f"   Valid: {is_valid_bad} (should be False)")
    print(f"   Issues detected: {len(issues_bad)}")
    
    # Success if good content has fewer issues than bad content and bad content is invalid
    success = (len(issues) < len(issues_bad)) and (not is_valid_bad)
    if success:
        print(f"\n✅ Validator correctly distinguishes quality (good: {len(issues)} issues, bad: {len(issues_bad)} issues)")
    
    return success


def main():
    """Run all dry-run tests."""
    print("\n" + "="*80)
    print("QUALITY IMPROVEMENT SYSTEM - DRY RUN TESTS")
    print("="*80)
    print("\nTesting all components without calling AI APIs...")
    
    results = []
    
    # Test 1: Research parsing and validation
    test1_result, research = test_research_parsing()
    results.append(("Research Parsing & Validation", test1_result))
    
    if not test1_result:
        print("\n❌ Research parsing failed - cannot continue")
        return 1
    
    # Test 2: Enhanced task creation
    test2_result = test_enhanced_task_creation(research)
    results.append(("Enhanced Task Creation", test2_result))
    
    # Test 3: Content validation
    test3_result = test_content_validation()
    results.append(("Content Validation", test3_result))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"\n{status}: {test_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! Quality improvement system is working correctly.")
        print("\n📋 Next Steps:")
        print("   1. Run unit tests: pytest src/tests/test_quality_improvements.py -v")
        print("   2. Test with real blog generation (requires API keys)")
        print("   3. Measure quality improvements on actual output")
        return 0
    else:
        print("\n❌ Some tests failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
