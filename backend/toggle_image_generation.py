#!/usr/bin/env python3
"""
Image Generation Toggle Script

This script allows easy toggling of AI image generation features for cost management.
Run this script to enable/disable image generation without code changes.
"""

import os
import sys
from pathlib import Path

def update_env_file(enable_images: bool = False):
    """Update .env file with image generation settings"""
    backend_dir = Path(__file__).parent
    env_file = backend_dir / ".env"
    
    # Settings to apply
    settings = {
        "ENABLE_AI_IMAGE_GENERATION": "true" if enable_images else "false",
        "ENABLE_HERO_IMAGE_GENERATION": "true" if enable_images else "false", 
        "ENABLE_CONTENT_IMAGE_INJECTION": "true" if enable_images else "false"
    }
    
    # Read existing .env content
    env_lines = []
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_lines = f.readlines()
    
    # Update or add settings
    updated_lines = []
    settings_updated = set()
    
    for line in env_lines:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            key = line.split('=')[0].strip()
            if key in settings:
                updated_lines.append(f"{key}={settings[key]}")
                settings_updated.add(key)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    # Add any missing settings
    for key, value in settings.items():
        if key not in settings_updated:
            updated_lines.append(f"{key}={value}")
    
    # Write updated .env file
    with open(env_file, 'w') as f:
        for line in updated_lines:
            f.write(line + '\n')
    
    print(f"✅ Updated {env_file}")
    for key, value in settings.items():
        print(f"   {key}={value}")

def main():
    """Main script function"""
    if len(sys.argv) != 2 or sys.argv[1] not in ['enable', 'disable']:
        print("Usage: python toggle_image_generation.py [enable|disable]")
        print("")
        print("Examples:")
        print("  python toggle_image_generation.py disable  # Disable AI image generation (save costs)")
        print("  python toggle_image_generation.py enable   # Enable AI image generation")
        sys.exit(1)
    
    action = sys.argv[1]
    enable_images = action == 'enable'
    
    print(f"🔧 {'Enabling' if enable_images else 'Disabling'} AI image generation...")
    
    update_env_file(enable_images)
    
    if enable_images:
        print("\n✅ AI image generation ENABLED")
        print("   - Hero images will be generated using OpenAI DALL-E")
        print("   - Content images will be automatically injected")
        print("   - Higher costs due to OpenAI API usage")
    else:
        print("\n❌ AI image generation DISABLED")
        print("   - No OpenAI image generation (cost savings)")
        print("   - Only free Unsplash images will be used when needed")
        print("   - Reduced API costs")
    
    print(f"\n🔄 Restart the backend server to apply changes:")
    print(f"   cd backend && source .venv/bin/activate && python src/main.py")

if __name__ == "__main__":
    main()
