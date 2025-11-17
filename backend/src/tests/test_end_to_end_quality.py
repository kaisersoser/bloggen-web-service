#!/usr/bin/env python3
"""
End-to-End Quality Improvement Test

Generates a real blog post and measures quality metrics to validate improvements.
Tests the complete workflow: research → parsing → validation → content → validation

Usage:
    cd backend
    source .venv/bin/activate
    python test_end_to_end_quality.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bloggen.flows import BlogGenerationFlow
from bloggen.schemas.research_schema import StructuredResearchOutput
from bloggen.research_parser import ResearchOutputParser
from bloggen.quality_validator import QualityValidator


def count_markdown_citations(content: str) -> int:
    """Count markdown link citations in content."""
    import re
    citations = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', content)
    return len(citations)


def count_words(content: str) -> int:
    """Count words in content."""
    return len(content.split())


def count_sections(content: str) -> int:
    """Count markdown headers (sections)."""
    import re
    sections = re.findall(r'^#+\s+.+$', content, re.MULTILINE)
    return len(sections)


def analyze_content_quality(content: str, structured_research: Optional[StructuredResearchOutput] = None):
    """Analyze content and return quality metrics."""
    
    print("\n" + "="*80)
    print("CONTENT QUALITY ANALYSIS")
    print("="*80)
    
    # Basic metrics
    word_count = count_words(content)
    citation_count = count_markdown_citations(content)
    section_count = count_sections(content)
    
    print(f"\n📊 Basic Metrics:")
    print(f"   Word Count: {word_count}")
    print(f"   Citations: {citation_count}")
    print(f"   Sections: {section_count}")
    print(f"   Words per Citation: {word_count / max(citation_count, 1):.1f}")
    
    # Validation
    is_valid, issues, metrics = QualityValidator.validate_content_quality(content, structured_research)
    
    print(f"\n✅ Validation Results:")
    print(f"   Valid: {is_valid}")
    print(f"   Issues Found: {len(issues)}")
    
    if issues:
        print(f"\n⚠️  Issues:")
        for issue in issues:
            print(f"   - {issue}")
    
    print(f"\n📈 Detailed Metrics:")
    for key, value in metrics.items():
        print(f"   {key}: {value}")
    
    # Quality grade
    if word_count >= 1800 and citation_count >= 10 and is_valid:
        grade = "A+ (Excellent)"
    elif word_count >= 1500 and citation_count >= 7 and is_valid:
        grade = "A (Very Good)"
    elif word_count >= 1200 and citation_count >= 5:
        grade = "B (Good)"
    elif word_count >= 800 and citation_count >= 3:
        grade = "C (Acceptable)"
    else:
        grade = "D (Needs Improvement)"
    
    print(f"\n🎯 Overall Grade: {grade}")
    
    return {
        "word_count": word_count,
        "citation_count": citation_count,
        "section_count": section_count,
        "is_valid": is_valid,
        "issues": issues,
        "grade": grade,
        "metrics": metrics
    }


def test_blog_generation(topic: str, test_name: str):
    """Generate a blog and analyze its quality."""
    
    print("\n" + "="*80)
    print(f"END-TO-END TEST: {test_name}")
    print("="*80)
    print(f"\n📝 Topic: {topic}")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Storage for results
    results = {
        "topic": topic,
        "test_name": test_name,
        "started_at": datetime.now().isoformat(),
        "phases": {}
    }
    
    try:
        # Initialize flow
        print("\n🔧 Initializing BlogGenerationFlow...")
        
        # Note: Config import has path issues in standalone script
        # Flow will initialize with default config from environment
        
        flow = BlogGenerationFlow()
        print("   Flow initialized with environment configuration")
        
        # Status callback for tracking
        def status_callback(step, progress, details):
            print(f"   [{step}] {progress}% - {details}")
        
        # Kickoff generation
        print("\n🚀 Starting blog generation...")
        print("   This may take 3-5 minutes depending on API response times...")
        
        result = flow.kickoff(
            inputs={
                "topic": topic,
                "instructions": "Focus on technical depth with specific examples and data."
            }
        )
        
        print("\n✅ Blog generation complete!")
        
        # Extract content
        if hasattr(result, 'raw'):
            content = result.raw
        elif isinstance(result, dict):
            content = result.get('final_content', '')
        else:
            content = str(result)
        
        # Analyze content
        analysis = analyze_content_quality(content)
        results["content_analysis"] = analysis
        results["completed_at"] = datetime.now().isoformat()
        
        # Save blog
        output_dir = Path(__file__).parent / "generated_blogs" / "quality_tests"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        blog_file = output_dir / f"{test_name}_{timestamp}.md"
        
        with open(blog_file, "w") as f:
            f.write(f"# Test: {test_name}\n")
            f.write(f"# Topic: {topic}\n")
            f.write(f"# Generated: {timestamp}\n\n")
            f.write("---\n\n")
            f.write(content)
        
        print(f"\n💾 Blog saved to: {blog_file}")
        
        # Save results
        results_file = output_dir / f"{test_name}_{timestamp}_results.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"📊 Results saved to: {results_file}")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Error during blog generation: {e}")
        import traceback
        traceback.print_exc()
        results["error"] = str(e)
        results["completed_at"] = datetime.now().isoformat()
        return results


def main():
    """Run end-to-end quality tests."""
    
    print("\n" + "="*80)
    print("QUALITY IMPROVEMENT END-TO-END TESTING")
    print("="*80)
    print("\nThis script will generate a real blog post and measure quality metrics.")
    print("Expected improvements:")
    print("  ✅ 1800+ words (vs previous ~500-800)")
    print("  ✅ 10+ inline citations (vs previous 2-3)")
    print("  ✅ Rich factual content with statistics and quotes")
    print("  ✅ Structured research validation")
    print("  ✅ Quality validation gates with retry logic")
    
    # Test topic
    topic = "GraphQL vs REST APIs in 2025"
    
    # Run test
    results = test_blog_generation(topic, "quality_improvement_test")
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if "content_analysis" in results:
        analysis = results["content_analysis"]
        print(f"\n✅ Test completed successfully!")
        print(f"   Grade: {analysis['grade']}")
        print(f"   Word Count: {analysis['word_count']}")
        print(f"   Citations: {analysis['citation_count']}")
        print(f"   Validation: {'PASSED' if analysis['is_valid'] else 'FAILED'}")
        
        # Improvement assessment
        print("\n📈 Quality Improvement Assessment:")
        
        if analysis['word_count'] >= 1800:
            print("   ✅ Word count meets target (1800+)")
        elif analysis['word_count'] >= 1500:
            print("   ⚠️  Word count good but below target (1500-1799)")
        else:
            print("   ❌ Word count below target (<1500)")
        
        if analysis['citation_count'] >= 10:
            print("   ✅ Citations meet target (10+)")
        elif analysis['citation_count'] >= 5:
            print("   ⚠️  Citations good but below target (5-9)")
        else:
            print("   ❌ Citations below target (<5)")
        
        if analysis['is_valid']:
            print("   ✅ Content passes quality validation")
        else:
            print(f"   ❌ Content failed validation: {len(analysis['issues'])} issues")
        
        # Overall assessment
        if (analysis['word_count'] >= 1800 and 
            analysis['citation_count'] >= 10 and 
            analysis['is_valid']):
            print("\n🎉 SUCCESS! Blog quality meets all improvement targets!")
            return 0
        elif (analysis['word_count'] >= 1500 and 
              analysis['citation_count'] >= 7):
            print("\n✅ GOOD! Blog quality shows significant improvement!")
            return 0
        else:
            print("\n⚠️  PARTIAL SUCCESS. Some improvements but targets not fully met.")
            return 1
    else:
        print("\n❌ Test failed - no analysis available")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
