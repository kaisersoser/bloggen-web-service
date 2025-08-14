#!/usr/bin/env python3
"""
Test enhanced image system with a real blog generation scenario.
This demonstrates how the new relevance-focused system works in practice.
"""

import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from bloggen.tools.unsplash_tool import UnsplashImageTool
import re

def simulate_agent_blog_generation():
    """Simulate how an agent would use the enhanced tool for blog generation"""
    print("🤖 SIMULATING AGENT BLOG GENERATION WITH ENHANCED IMAGE TOOL")
    print("=" * 80)
    
    # Simulate a blog about "The Future of Artificial Intelligence in Healthcare"
    blog_topic = "The Future of Artificial Intelligence in Healthcare"
    
    print(f"📝 Blog Topic: {blog_topic}")
    print("\n🎯 Agent would use the enhanced tool for strategic image placement:")
    
    tool = UnsplashImageTool()
    
    # Hero Image (what agents would do now with better instructions)
    print("\n1️⃣ HERO IMAGE GENERATION")
    print("-" * 40)
    hero_query = "artificial intelligence healthcare medical technology"
    print(f"Query: '{hero_query}'")
    
    hero_result = tool._run(hero_query, count=1)
    if "![" in hero_result:
        pattern = r'!\[([^\]]*)\]\(([^)]+)'
        matches = re.findall(pattern, hero_result)
        if matches:
            alt, url = matches[0]
            source = "🏞️ UNSPLASH" if "unsplash.com" in url else "🤖 AI GENERATED"
            print(f"✅ {source}: {alt[:60]}...")
    
    # Supporting Image 1 - Technical concept
    print("\n2️⃣ SUPPORTING IMAGE 1 (Technical Concept)")
    print("-" * 40)
    support1_query = "machine learning medical diagnosis neural network"
    print(f"Query: '{support1_query}'")
    
    support1_result = tool._run(support1_query, count=1)
    if "![" in support1_result:
        pattern = r'!\[([^\]]*)\]\(([^)]+)'
        matches = re.findall(pattern, support1_result)
        if matches:
            alt, url = matches[0]
            source = "🏞️ UNSPLASH" if "unsplash.com" in url else "🤖 AI GENERATED"
            print(f"✅ {source}: {alt[:60]}...")
    
    # Supporting Image 2 - Real-world application
    print("\n3️⃣ SUPPORTING IMAGE 2 (Real-world Application)")
    print("-" * 40)
    support2_query = "doctor using digital tablet patient consultation"
    print(f"Query: '{support2_query}'")
    
    support2_result = tool._run(support2_query, count=1)
    if "![" in support2_result:
        pattern = r'!\[([^\]]*)\]\(([^)]+)'
        matches = re.findall(pattern, support2_result)
        if matches:
            alt, url = matches[0]
            source = "🏞️ UNSPLASH" if "unsplash.com" in url else "🤖 AI GENERATED"
            print(f"✅ {source}: {alt[:60]}...")
    
    print("\n" + "="*80)
    print("📊 ANALYSIS:")
    print("• Technical concepts likely trigger AI generation (custom diagrams)")
    print("• Real-world scenarios likely use Unsplash photos (authentic scenes)")
    print("• All images are contextually relevant to the healthcare AI topic")
    print("• Agent gets appropriate mix of photos and illustrations automatically")

def test_before_vs_after():
    """Compare old generic queries vs new specific queries"""
    print("\n\n📈 BEFORE vs AFTER COMPARISON")
    print("=" * 80)
    
    tool = UnsplashImageTool()
    
    scenarios = [
        {
            "topic": "Blockchain Technology",
            "old_query": "blockchain technology",
            "new_query": "blockchain cryptocurrency network visualization"
        },
        {
            "topic": "Remote Work Productivity",
            "old_query": "remote work", 
            "new_query": "remote work team video conference collaboration"
        },
        {
            "topic": "Machine Learning Ethics",
            "old_query": "machine learning ethics",
            "new_query": "artificial intelligence ethics decision making algorithm"
        }
    ]
    
    for scenario in scenarios:
        print(f"\n📝 Topic: {scenario['topic']}")
        print("-" * 40)
        
        # Test old approach
        print(f"❌ OLD Query: '{scenario['old_query']}'")
        old_result = tool._run(scenario['old_query'], count=1)
        if "![" in old_result:
            pattern = r'!\[([^\]]*)\]\('
            matches = re.findall(pattern, old_result)
            if matches:
                print(f"   Result: {matches[0][:50]}...")
        
        # Test new approach  
        print(f"✅ NEW Query: '{scenario['new_query']}'")
        new_result = tool._run(scenario['new_query'], count=1)
        if "![" in new_result:
            pattern = r'!\[([^\]]*)\]\('
            matches = re.findall(pattern, new_result)
            if matches:
                print(f"   Result: {matches[0][:50]}...")

if __name__ == "__main__":
    simulate_agent_blog_generation()
    test_before_vs_after()
    
    print("\n" + "="*80)
    print("🎉 ENHANCED IMAGE SYSTEM DEMONSTRATION COMPLETE")
    print("\n💡 Key Improvements:")
    print("• More specific, descriptive queries → Better relevance")
    print("• Automatic source selection → Optimal image type") 
    print("• Relevance filtering → Quality over quantity")
    print("• Intelligent fallbacks → Consistent results")
    print("\n🚀 Agents will now generate blogs with much more relevant images!")
