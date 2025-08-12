#!/usr/bin/env python3
"""
Direct test of the Unsplash tool to verify image URL generation.
"""

import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from bloggen.tools.unsplash_tool import UnsplashImageTool
import requests
import re

def test_unsplash_tool():
    """Test the Unsplash tool directly"""
    print("🔍 TESTING UNSPLASH TOOL DIRECTLY")
    print("=" * 50)
    
    # Initialize the tool
    tool = UnsplashImageTool()
    
    # Test with a simple query
    query = "technology"
    print(f"Searching for: {query}")
    
    # Get the image result
    result = tool._run(query=query, count=1, orientation="landscape")
    
    print(f"\n📝 Generated Markdown:")
    print(result)
    print("\n" + "="*50)
    
    # Extract the image URL from the markdown
    pattern = r'!\[([^\]]*)\]\(([^)]+)(?:\s+"([^"]*)")?\)'
    matches = re.findall(pattern, result)
    
    if matches:
        alt, url, title = matches[0]
        print(f"\n🔗 Extracted URL: {url}")
        
        # Test if the URL is accessible
        print(f"\n🧪 Testing URL accessibility...")
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            print(f"Status Code: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            
            if response.status_code == 200:
                print("✅ SUCCESS: Fresh URL is accessible!")
                return True
            else:
                print(f"❌ FAILED: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            return False
    else:
        print("❌ No image URLs found in the result")
        return False

if __name__ == "__main__":
    test_unsplash_tool()
