#!/usr/bin/env python3
"""
Test the specific Nova Scotia image URL.
"""

import requests

def test_nova_scotia_image():
    """Test the specific Nova Scotia image URL"""
    
    print("🔍 TESTING NOVA SCOTIA IMAGE URL")
    print("=" * 50)
    
    url = "https://images.unsplash.com/photo-1584240368813-b5e4b1c2d5e7?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=MnwzNjUyOXwwfDF8c2VhcmNofDN8fG5vdmF8ZW58MHx8fHwxNjEzNDUxMjAx&ixlib=rb-1.2.1&q=80&w=1080"
    
    print(f"URL: {url}")
    
    try:
        # Test if the URL is accessible
        response = requests.head(url, timeout=10, allow_redirects=True)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        print(f"Content-Length: {response.headers.get('Content-Length', 'Unknown')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'image' in content_type:
                print(f"✅ VALID: Image is accessible and valid")
                
                # Try to get the actual image
                print("\n🖼️ Downloading image to verify...")
                img_response = requests.get(url, timeout=10)
                if img_response.status_code == 200:
                    print(f"✅ DOWNLOAD SUCCESS: {len(img_response.content)} bytes")
                    return True
                else:
                    print(f"❌ DOWNLOAD FAILED: {img_response.status_code}")
                    return False
            else:
                print(f"❌ INVALID: Not an image (Content-Type: {content_type})")
                return False
        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            return False
        
    except requests.exceptions.RequestException as e:
        print(f"❌ CONNECTION ERROR: {e}")
        return False

if __name__ == "__main__":
    test_nova_scotia_image()
