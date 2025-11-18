#!/usr/bin/env python3
"""
Test Image Scoring Logic

Tests the relevance scoring to understand why images might be rejected.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test queries from the actual blog
test_queries = [
    "AI interface laptop",
    "machine learning artificial intelligence technology",
    "quantum computer technology",
    "artificial intelligence trends",
    "machine learning professional business"
]

# Simulate image metadata similar to what Unsplash returns
test_images = [
    {
        "alt_description": "person using laptop computer",
        "description": "AI and technology interface on laptop screen",
        "tags": [
            {"title": "laptop"},
            {"title": "computer"},
            {"title": "technology"},
            {"title": "business"}
        ]
    },
    {
        "alt_description": "artificial intelligence concept",
        "description": "machine learning neural network visualization",
        "tags": [
            {"title": "artificial intelligence"},
            {"title": "machine learning"},
            {"title": "technology"}
        ]
    },
    {
        "alt_description": "quantum computing hardware",
        "description": "quantum computer processor technology",
        "tags": [
            {"title": "quantum"},
            {"title": "computer"},
            {"title": "technology"},
            {"title": "science"}
        ]
    }
]

def score_image_relevance(image: dict, original_query: str, enhanced_query: str) -> float:
    """Replicate the scoring logic from unsplash_tool.py"""
    score = 0.0
    
    # Get image metadata
    alt_description = (image.get("alt_description") or "").lower()
    description = (image.get("description") or "").lower()
    tags = []
    if image.get("tags"):
        tags = [
            tag.get("title", "").lower()
            for tag in image["tags"]
            if tag.get("title")
        ]
    
    # Combine all text sources
    image_text = f"{alt_description} {description} {' '.join(tags)}"
    
    # Extract key terms from queries
    original_terms = set(original_query.lower().split())
    enhanced_terms = set(enhanced_query.lower().split())
    all_query_terms = original_terms.union(enhanced_terms)
    
    # WEIGHTED SCORING: Exact term matches
    exact_matches = 0
    matched_terms = []
    for term in all_query_terms:
        if len(term) > 2 and term in image_text:
            exact_matches += 1
            matched_terms.append(term)
            score += 0.3
    
    # Bonus for multiple exact matches
    if exact_matches >= 3:
        score += 0.2
    elif exact_matches >= 2:
        score += 0.1
    
    # Semantic relevance (simplified)
    semantic_score = calculate_semantic_relevance(image_text, original_query)
    score += semantic_score
    
    # Quality indicators (minor boost)
    downloads = image.get("downloads", 0)
    likes = image.get("likes", 0)
    if downloads > 1000:
        score += 0.05
    if likes > 100:
        score += 0.03
    
    # Cap at 1.0
    final_score = min(score, 1.0)
    
    return final_score, exact_matches, matched_terms, semantic_score

def calculate_semantic_relevance(image_text: str, query: str) -> float:
    """Simplified semantic scoring"""
    semantic_groups = {
        "technology": ["tech", "digital", "computer", "software", "coding", "algorithm", "system"],
        "ai_ml": ["artificial", "intelligence", "machine", "learning", "neural", "deep", "model"],
        "business": ["business", "corporate", "office", "professional", "meeting", "team"],
    }
    
    query_lower = query.lower()
    semantic_score = 0.0
    
    for group_name, keywords in semantic_groups.items():
        query_matches = sum(1 for keyword in keywords if keyword in query_lower)
        if query_matches > 0:
            image_matches = sum(1 for keyword in keywords if keyword in image_text)
            if image_matches > 0:
                group_score = min(image_matches / len(keywords), 0.25)
                semantic_score += group_score
    
    return min(semantic_score, 0.25)

print("="*80)
print("IMAGE RELEVANCE SCORING DIAGNOSIS")
print("="*80)
print(f"\n🎯 Current Threshold: 0.6 (60%)")
print(f"⚠️  Issue: Images may be scoring too low to pass threshold\n")

for query in test_queries:
    print(f"\n{'='*80}")
    print(f"Query: '{query}'")
    print(f"{'='*80}")
    
    for i, image in enumerate(test_images):
        score, exact_matches, matched_terms, semantic = score_image_relevance(
            image, query, query
        )
        
        status = "✅ PASS (≥0.6)" if score >= 0.6 else "❌ FAIL (<0.6)"
        
        print(f"\nImage {i+1}: {image['alt_description'][:50]}")
        print(f"  Final Score: {score:.2f} {status}")
        print(f"  Exact Matches: {exact_matches} terms {matched_terms}")
        print(f"  Semantic Score: {semantic:.2f}")
        print(f"  Breakdown:")
        print(f"    - Exact matches: {exact_matches} × 0.3 = {exact_matches * 0.3:.2f}")
        if exact_matches >= 3:
            print(f"    - Multi-match bonus: +0.2")
        elif exact_matches >= 2:
            print(f"    - Multi-match bonus: +0.1")
        print(f"    - Semantic relevance: +{semantic:.2f}")
        print(f"    - Quality indicators: +0.08 (if high quality)")

print("\n" + "="*80)
print("ANALYSIS & RECOMMENDATIONS")
print("="*80)
print("""
🔍 Issue Identified:
   The 0.6 threshold requires images to have either:
   - 2+ exact keyword matches (0.6 points minimum)
   - OR 1 exact match + high semantic score + bonuses
   
   This is TOO STRICT for general queries where Unsplash images may use
   synonyms or related terms rather than exact keywords.

💡 Recommended Solutions:

   Option 1: Lower threshold to 0.5 (50%)
   - More balanced between quality and acceptance rate
   - Still filters out truly irrelevant images
   - Allows good images with 1-2 keyword matches
   
   Option 2: Adjust scoring weights
   - Reduce exact match weight: 0.3 → 0.25
   - Increase semantic scoring cap: 0.25 → 0.35
   - This rewards semantic relevance more
   
   Option 3: Implement smart threshold
   - 0.6 for first attempt
   - 0.5 for second attempt (query variation)
   - 0.4 for third attempt before AI fallback
   
🎯 Recommendation: Use Option 1 or Option 3
   Option 1 is fastest to implement and test.
   Option 3 provides best balance of quality and success rate.
""")
