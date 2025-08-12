#!/usr/bin/env python3
"""
Test if the image URLs in the generated blog are valid and accessible.
"""

import requests
import re
import sys
import os

def test_image_urls():
    """Test if image URLs in the blog are valid and accessible"""
    
    print("🔍 TESTING IMAGE URL VALIDITY")
    print("=" * 50)
    
    # Read the current blog
    blog_path = "/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/generated_blogs/blog.md"
    
    try:
        with open(blog_path, 'r') as f:
            content = f.read()
        
        # Extract image URLs
        image_pattern = r'!\[.*?\]\((.*?)\)'
        images = re.findall(image_pattern, content)
        
        print(f"📸 Found {len(images)} images in the blog:")
        print(f"📝 Blog preview: {content[:200]}...")
        
        # Show each match with context
        for match in re.finditer(image_pattern, content):
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end]
            print(f"🔍 Image context: ...{context}...")
        
        for i, url in enumerate(images, 1):
            print(f"\n{i}. Testing: {url}")
            
            try:
                # Test if the URL is accessible
                response = requests.head(url, timeout=10, allow_redirects=True)
                
                print(f"   Status Code: {response.status_code}")
                print(f"   Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
                print(f"   Content-Length: {response.headers.get('Content-Length', 'Unknown')}")
                
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '')
                    if 'image' in content_type:
                        print(f"   ✅ VALID: Image is accessible")
                    else:
                        print(f"   ❌ INVALID: Not an image (Content-Type: {content_type})")
                elif response.status_code == 404:
                    print(f"   ❌ INVALID: Image not found (404)")
                elif response.status_code in [403, 429]:
                    print(f"   ⚠️  BLOCKED: Access restricted ({response.status_code})")
                else:
                    print(f"   ❌ ERROR: HTTP {response.status_code}")
                
            except requests.exceptions.RequestException as e:
                print(f"   ❌ CONNECTION ERROR: {e}")
        
        return images
        
    except Exception as e:
        print(f"❌ Error reading blog: {e}")
        return []

if __name__ == "__main__":
    test_image_urls()
