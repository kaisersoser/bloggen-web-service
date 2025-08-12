#!/usr/bin/env python3
"""
Test the specific Himalayas image URL to verify if it's a real Unsplash URL or agent hallucination.
"""

import requests

def test_himalayas_image():
    """Test the specific Himalayas image URL from the current blog"""
    
    print("🔍 TESTING HIMALAYAS IMAGE URL FROM CURRENT BLOG")
    print("=" * 60)
    
    url = "https://images.unsplash.com/photo-1507319104839-10b224c4f2c0?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=MnwzNjUyOXwwfDF8c2VhcmNofDd8fGhpbWFsYXlhfGVufDB8fHx8MTY4NjM0NzYxNw&ixlib=rb-4.0.3&q=80&w=1080"
    
    print(f"URL: {url}")
    print()
    
    try:
        # Test if the URL is accessible
        response = requests.head(url, timeout=10, allow_redirects=True)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        print(f"Content-Length: {response.headers.get('Content-Length', 'Unknown')}")
        print(f"Server: {response.headers.get('Server', 'Unknown')}")
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            if 'image' in content_type:
                print(f"\n✅ VALID: Image is accessible and valid")
                
                # Try to get the actual image to confirm
                print("\n🖼️ Downloading image to verify...")
                img_response = requests.get(url, timeout=10)
                if img_response.status_code == 200:
                    print(f"✅ DOWNLOAD SUCCESS: {len(img_response.content)} bytes")
                    print("🎯 CONCLUSION: This is a REAL Unsplash URL")
                    return True
                else:
                    print(f"❌ DOWNLOAD FAILED: {img_response.status_code}")
                    return False
            else:
                print(f"❌ INVALID: Not an image (Content-Type: {content_type})")
                return False
        elif response.status_code == 404:
            print(f"❌ NOT FOUND: HTTP 404 - This URL does not exist")
            print("🚨 CONCLUSION: This appears to be a HALLUCINATED URL")
            return False
        else:
            print(f"❌ ERROR: HTTP {response.status_code}")
            return False
        
    except requests.exceptions.RequestException as e:
        print(f"❌ CONNECTION ERROR: {e}")
        return False

def analyze_url_structure():
    """Analyze the URL structure to see if it matches real Unsplash patterns"""
    
    print("\n🔬 ANALYZING URL STRUCTURE")
    print("=" * 40)
    
    url = "https://images.unsplash.com/photo-1507319104839-10b224c4f2c0?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=MnwzNjUyOXwwfDF8c2VhcmNofDd8fGhpbWFsYXlhfGVufDB8fHx8MTY4NjM0NzYxNw&ixlib=rb-4.0.3&q=80&w=1080"
    
    # Break down the URL
    parts = url.split('?')
    base_url = parts[0]
    params = parts[1] if len(parts) > 1 else ""
    
    print(f"Base URL: {base_url}")
    print(f"Parameters: {params}")
    
    # Extract photo ID
    photo_id = base_url.split('/')[-1]
    print(f"Photo ID: {photo_id}")
    
    # Check if this follows typical Unsplash pattern
    if base_url.startswith("https://images.unsplash.com/photo-"):
        print("✅ URL structure matches Unsplash pattern")
    else:
        print("❌ URL structure does NOT match Unsplash pattern")
    
    # Check parameters
    expected_params = ['crop', 'cs', 'fit', 'fm', 'ixid', 'ixlib', 'q', 'w']
    found_params = [p.split('=')[0] for p in params.split('&')]
    
    print(f"Expected params: {expected_params}")
    print(f"Found params: {found_params}")
    
    missing = set(expected_params) - set(found_params)
    extra = set(found_params) - set(expected_params)
    
    if not missing and not extra:
        print("✅ Parameters match expected Unsplash format")
    else:
        print(f"⚠️ Parameter differences - Missing: {missing}, Extra: {extra}")

if __name__ == "__main__":
    # Test the URL
    is_valid = test_himalayas_image()
    
    # Analyze structure regardless of validity
    analyze_url_structure()
    
    print(f"\n📊 FINAL VERDICT:")
    if is_valid:
        print("🎯 This is a REAL Unsplash URL that works correctly")
    else:
        print("🚨 This appears to be a HALLUCINATED URL - either agent-generated or expired")
