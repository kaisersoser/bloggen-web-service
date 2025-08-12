#!/usr/bin/env python3
"""
Quick API test to demonstrate the enhanced flow produces clean results.
"""

import requests
import json

def test_enhanced_api():
    """Test the enhanced API to see if it now produces clean results"""
    
    print("🧪 TESTING ENHANCED API ENDPOINT")
    print("=" * 50)
    
    # Test the legacy API (what frontend uses)
    legacy_url = "http://localhost:5000/generate-blog"
    
    payload = {
        "user_id": "test_user_api",
        "topic": "AI Content Creation Tools",
        "instructions": "Focus on 2025 tools and include practical examples"
    }
    
    try:
        print("🚀 Sending request to legacy API...")
        response = requests.post(legacy_url, json=payload, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('content', '')
            
            print(f"✅ API call successful!")
            print(f"📊 Content length: {len(content)} characters")
            
            # Quick image analysis
            import re
            image_pattern = r'!\[.*?\]\((.*?)\)'
            images = re.findall(image_pattern, content)
            
            print(f"🖼️ Images found: {len(images)}")
            
            deprecated_count = 0
            valid_count = 0
            
            for img_url in images:
                if 'source.unsplash.com' in img_url:
                    deprecated_count += 1
                    print(f"   ❌ DEPRECATED: {img_url}")
                elif 'images.unsplash.com' in img_url:
                    valid_count += 1
                    print(f"   ✅ VALID: {img_url[:60]}...")
                else:
                    print(f"   ❓ OTHER: {img_url[:60]}...")
            
            print(f"\n📈 RESULTS:")
            print(f"   📸 Total Images: {len(images)}")
            print(f"   ✅ Valid Images: {valid_count}")
            print(f"   ❌ Deprecated Images: {deprecated_count}")
            print(f"   🎯 Success: {'YES' if deprecated_count == 0 and valid_count > 0 else 'NO'}")
            
            return content, deprecated_count == 0 and valid_count > 0
            
        else:
            print(f"❌ API call failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None, False
            
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return None, False

if __name__ == "__main__":
    test_enhanced_api()
