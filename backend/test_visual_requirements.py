#!/usr/bin/env python3
"""
Test the enhanced visual requirements (2-3 images per blog).
"""

import sys
import os
import re

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def count_images_in_content(content: str) -> dict:
    """Count and analyze images in blog content"""
    # Pattern for markdown images: ![alt](url "optional title")
    pattern = r'!\[([^\]]*)\]\(([^)]+)(?:\s+"([^"]*)")?\)'
    matches = re.findall(pattern, content)
    
    image_analysis = {
        'total_images': len(matches),
        'images': [],
        'unsplash_count': 0,
        'ai_generated_count': 0,
        'placeholder_count': 0,
        'positions': []
    }
    
    # Analyze each image
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('!['):
            image_analysis['positions'].append(i + 1)  # Line number (1-indexed)
    
    for alt, url, title in matches:
        image_info = {
            'alt': alt,
            'url': url,
            'title': title
        }
        
        # Categorize image source
        if 'images.unsplash.com' in url:
            image_analysis['unsplash_count'] += 1
            image_info['source'] = 'unsplash'
        elif 'oaidalleapiprodscus.blob.core.windows.net' in url or 'dalle' in url.lower():
            image_analysis['ai_generated_count'] += 1
            image_info['source'] = 'ai_generated'
        elif 'placeholder' in url.lower() or 'placehold' in url.lower():
            image_analysis['placeholder_count'] += 1
            image_info['source'] = 'placeholder'
        else:
            image_info['source'] = 'unknown'
        
        image_analysis['images'].append(image_info)
    
    return image_analysis

def analyze_image_placement(content: str, image_analysis: dict) -> dict:
    """Analyze strategic placement of images"""
    lines = content.split('\n')
    total_lines = len(lines)
    
    # Find introduction end (usually after first few paragraphs)
    intro_end = 0
    paragraph_count = 0
    for i, line in enumerate(lines):
        if line.strip() and not line.startswith('#'):
            if line.strip() and i > 0 and lines[i-1].strip() == '':
                paragraph_count += 1
                if paragraph_count >= 2:  # After 2 paragraphs likely end of intro
                    intro_end = i
                    break
    
    placement_analysis = {
        'hero_image_present': False,
        'images_distributed': False,
        'image_spacing': [],
        'content_length': total_lines,
        'intro_end_line': intro_end
    }
    
    # Check for hero image (should be early in content)
    if image_analysis['positions']:
        first_image_line = image_analysis['positions'][0]
        if first_image_line <= intro_end + 10:  # Within reasonable range after intro
            placement_analysis['hero_image_present'] = True
    
    # Analyze spacing between images
    positions = image_analysis['positions']
    if len(positions) > 1:
        for i in range(1, len(positions)):
            spacing = positions[i] - positions[i-1]
            placement_analysis['image_spacing'].append(spacing)
        
        # Check if images are reasonably distributed
        avg_spacing = sum(placement_analysis['image_spacing']) / len(placement_analysis['image_spacing'])
        if avg_spacing > 20:  # At least 20 lines between images
            placement_analysis['images_distributed'] = True
    
    return placement_analysis

def test_visual_requirements():
    """Test if the current blog meets visual requirements"""
    print("🎨 TESTING VISUAL REQUIREMENTS (2-3 IMAGES)")
    print("=" * 60)
    
    # Read the current blog
    blog_path = "/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/generated_blogs/blog.md"
    
    if not os.path.exists(blog_path):
        print(f"❌ Blog file not found: {blog_path}")
        return False
    
    with open(blog_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📄 Blog content length: {len(content)} characters")
    lines_count = len(content.split('\n'))
    print(f"📄 Blog lines: {lines_count} lines")
    
    # Analyze images
    image_analysis = count_images_in_content(content)
    placement_analysis = analyze_image_placement(content, image_analysis)
    
    print(f"\n🖼️ IMAGE ANALYSIS:")
    print(f"   Total images: {image_analysis['total_images']}")
    print(f"   Unsplash images: {image_analysis['unsplash_count']}")
    print(f"   AI generated images: {image_analysis['ai_generated_count']}")
    print(f"   Placeholder images: {image_analysis['placeholder_count']}")
    
    print(f"\n📍 IMAGE PLACEMENT:")
    print(f"   Image positions (line numbers): {image_analysis['positions']}")
    print(f"   Hero image present: {placement_analysis['hero_image_present']}")
    print(f"   Images well distributed: {placement_analysis['images_distributed']}")
    if placement_analysis['image_spacing']:
        print(f"   Spacing between images: {placement_analysis['image_spacing']} lines")
    
    print(f"\n📊 VISUAL REQUIREMENTS CHECK:")
    
    # Check minimum image requirement (2-3 images)
    meets_count = 2 <= image_analysis['total_images'] <= 3
    print(f"   ✅ 2-3 images: {meets_count} ({image_analysis['total_images']} images)")
    
    # Check for valid images (not placeholders)
    valid_images = image_analysis['total_images'] - image_analysis['placeholder_count']
    meets_validity = valid_images >= 2
    print(f"   ✅ Valid images: {meets_validity} ({valid_images} valid)")
    
    # Check placement
    meets_placement = placement_analysis['hero_image_present']
    print(f"   ✅ Hero image placement: {meets_placement}")
    
    meets_distribution = placement_analysis['images_distributed'] or image_analysis['total_images'] <= 2
    print(f"   ✅ Image distribution: {meets_distribution}")
    
    # Overall assessment
    overall_pass = meets_count and meets_validity and meets_placement
    print(f"\n🎯 OVERALL VISUAL ASSESSMENT: {'✅ PASS' if overall_pass else '❌ NEEDS IMPROVEMENT'}")
    
    if not overall_pass:
        print("\n💡 RECOMMENDATIONS:")
        if not meets_count:
            print("   - Ensure blog has 2-3 images (current guidelines)")
        if not meets_validity:
            print("   - Replace placeholder images with valid tool-generated images")
        if not meets_placement:
            print("   - Add hero image after introduction paragraph")
        if not meets_distribution:
            print("   - Distribute images more evenly throughout content")
    
    return overall_pass

if __name__ == "__main__":
    test_visual_requirements()
