#!/usr/bin/env python3
"""
Test all image URLs in the generated blog content.
"""

import requests
import re
import os

def extract_image_urls(markdown_content):
    """Extract all image URLs from markdown content"""
    # Pattern for markdown images: ![alt](url "optional title")
    pattern = r'!\[([^\]]*)\]\(([^)]+)(?:\s+"([^"]*)")?\)'
    matches = re.findall(pattern, markdown_content)
    return [(alt, url, title) for alt, url, title in matches]

def test_image_url(url, alt_text):
    """Test if an image URL is accessible"""
    print(f"\n🔍 Testing: {alt_text}")
    print(f"URL: {url}")
    
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        status = response.status_code
        content_type = response.headers.get('Content-Type', 'Unknown')
        
        print(f"Status: {status}")
        print(f"Content-Type: {content_type}")
        
        if status == 200:
            if 'image' in content_type:
                print("✅ VALID: Image is accessible")
                return True
            else:
                print(f"❌ INVALID: Not an image (Content-Type: {content_type})")
                return False
        else:
            print(f"❌ ERROR: HTTP {status}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ CONNECTION ERROR: {e}")
        return False

def main():
    """Test all images in the current blog"""
    print("🔍 TESTING ALL IMAGES IN GENERATED BLOG")
    print("=" * 60)
    
    # Read the current blog content
    blog_path = "/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/generated_blogs/blog.md"
    
    if not os.path.exists(blog_path):
        print(f"❌ Blog file not found: {blog_path}")
        return
    
    with open(blog_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📄 Blog content length: {len(content)} characters")
    
    # Extract all image URLs
    image_urls = extract_image_urls(content)
    
    if not image_urls:
        print("❌ No images found in the blog content")
        return
    
    print(f"\n🖼️ Found {len(image_urls)} images:")
    
    valid_count = 0
    for i, (alt, url, title) in enumerate(image_urls, 1):
        print(f"\n--- Image {i} ---")
        if test_image_url(url, alt):
            valid_count += 1
    
    print(f"\n📊 SUMMARY:")
    print(f"Total images: {len(image_urls)}")
    print(f"Valid images: {valid_count}")
    print(f"Invalid images: {len(image_urls) - valid_count}")
    
    if valid_count == len(image_urls):
        print("✅ ALL IMAGES ARE VALID!")
    else:
        print("❌ Some images are invalid and will show as placeholders in the frontend")

if __name__ == "__main__":
    main()
