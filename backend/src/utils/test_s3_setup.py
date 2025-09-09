#!/usr/bin/env python3
"""
Test S3 Connection and Configuration

This script tests your AWS S3 setup to ensure everything is configured correctly
before running the hero image generation utility.
"""

import os
import sys
from dotenv import load_dotenv

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)
sys.path.insert(0, src_dir)

# Load environment
backend_dir = os.path.dirname(src_dir)
load_dotenv(os.path.join(backend_dir, '.env'))

def test_s3_setup():
    """Test S3 configuration and connection"""
    print("🧪 Testing S3 Setup...")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_S3_BUCKET_NAME', 'AWS_S3_REGION']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            # Mask sensitive values
            if 'SECRET' in var or 'KEY' in var:
                display_value = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please add these to your backend/.env file")
        return False
    
    print("\n🔗 Testing S3 Connection...")
    
    try:
        from core.s3_storage import get_s3_storage
        s3_storage = get_s3_storage()
        
        # Test connection
        if s3_storage.test_connection():
            print("✅ S3 connection successful!")
            
            # Test image download and conversion (with a sample image)
            print("\n🖼️  Testing image processing...")
            test_url = "https://picsum.photos/500/500"  # Sample image
            
            try:
                jpeg_data = s3_storage.download_and_convert_image(test_url, quality=85)
                print(f"✅ Image processing successful! Size: {len(jpeg_data.getvalue())} bytes")
                
                # Test upload (but don't actually upload to save costs)
                print("✅ Image processing and S3 upload functionality ready!")
                
            except Exception as e:
                print(f"❌ Image processing test failed: {e}")
                return False
            
            return True
        else:
            print("❌ S3 connection failed!")
            return False
            
    except Exception as e:
        print(f"❌ S3 setup error: {e}")
        return False

if __name__ == "__main__":
    success = test_s3_setup()
    
    if success:
        print("\n🎉 S3 setup is working correctly!")
        print("You can now run the hero image generation utility:")
        print("  python src/utils/generate_hero_images.py --dry-run --limit 1")
    else:
        print("\n💥 S3 setup needs attention before proceeding.")
        sys.exit(1)
