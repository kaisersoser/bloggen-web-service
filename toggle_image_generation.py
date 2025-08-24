#!/usr/bin/env python3
"""
Image Generation Toggle Script

This script allows you to easily enable or disable AI image generation features
to control costs while maintaining the ability to quickly re-enable them.

Usage:
    python toggle_image_generation.py --disable    # Disable all AI image generation
    python toggle_image_generation.py --enable     # Enable all AI image generation
    python toggle_image_generation.py --status     # Show current status
    python toggle_image_generation.py --hero-only  # Enable only hero images (not content injection)
"""

import os
import argparse
from pathlib import Path

def get_env_file_path():
    """Get the path to the .env file"""
    return Path(__file__).parent / ".env"

def read_env_file():
    """Read current .env file content"""
    env_file = get_env_file_path()
    if env_file.exists():
        with open(env_file, 'r') as f:
            return f.read()
    return ""

def update_env_setting(content: str, key: str, value: str) -> str:
    """Update or add an environment variable in .env content"""
    lines = content.split('\n')
    updated = False
    
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            updated = True
            break
    
    if not updated:
        lines.append(f"{key}={value}")
    
    return '\n'.join(lines)

def write_env_file(content: str):
    """Write content to .env file"""
    env_file = get_env_file_path()
    with open(env_file, 'w') as f:
        f.write(content)

def get_current_status():
    """Get current image generation settings"""
    env_content = read_env_file()
    
    # Parse current settings (default to False if not set)
    ai_gen = "false"
    hero_gen = "false" 
    content_gen = "false"
    
    for line in env_content.split('\n'):
        if line.strip().startswith("ENABLE_AI_IMAGE_GENERATION="):
            ai_gen = line.split('=', 1)[1].strip()
        elif line.strip().startswith("ENABLE_HERO_IMAGE_GENERATION="):
            hero_gen = line.split('=', 1)[1].strip()
        elif line.strip().startswith("ENABLE_CONTENT_IMAGE_INJECTION="):
            content_gen = line.split('=', 1)[1].strip()
    
    return {
        'ai_image_generation': ai_gen.lower() == 'true',
        'hero_image_generation': hero_gen.lower() == 'true',
        'content_image_injection': content_gen.lower() == 'true'
    }

def print_status():
    """Print current image generation status"""
    status = get_current_status()
    
    print("\n🖼️  Image Generation Status:")
    print(f"   AI Image Generation (OpenAI): {'✅ Enabled' if status['ai_image_generation'] else '❌ Disabled'}")
    print(f"   Hero Image Generation: {'✅ Enabled' if status['hero_image_generation'] else '❌ Disabled'}")
    print(f"   Content Image Injection: {'✅ Enabled' if status['content_image_injection'] else '❌ Disabled'}")
    
    if not any(status.values()):
        print("\n💰 All AI image generation disabled - no OpenAI image costs")
    elif status['ai_image_generation']:
        print("\n💸 AI image generation enabled - OpenAI costs apply")
    
    print()

def disable_all():
    """Disable all AI image generation"""
    content = read_env_file()
    content = update_env_setting(content, "ENABLE_AI_IMAGE_GENERATION", "false")
    content = update_env_setting(content, "ENABLE_HERO_IMAGE_GENERATION", "false")
    content = update_env_setting(content, "ENABLE_CONTENT_IMAGE_INJECTION", "false")
    write_env_file(content)
    print("✅ All AI image generation disabled")

def enable_all():
    """Enable all AI image generation"""
    content = read_env_file()
    content = update_env_setting(content, "ENABLE_AI_IMAGE_GENERATION", "true")
    content = update_env_setting(content, "ENABLE_HERO_IMAGE_GENERATION", "true")
    content = update_env_setting(content, "ENABLE_CONTENT_IMAGE_INJECTION", "true")
    write_env_file(content)
    print("✅ All AI image generation enabled")

def enable_hero_only():
    """Enable only hero image generation (not content injection)"""
    content = read_env_file()
    content = update_env_setting(content, "ENABLE_AI_IMAGE_GENERATION", "true")
    content = update_env_setting(content, "ENABLE_HERO_IMAGE_GENERATION", "true")
    content = update_env_setting(content, "ENABLE_CONTENT_IMAGE_INJECTION", "false")
    write_env_file(content)
    print("✅ Hero image generation enabled, content injection disabled")

def main():
    parser = argparse.ArgumentParser(description="Toggle AI image generation features")
    parser.add_argument("--disable", action="store_true", help="Disable all AI image generation")
    parser.add_argument("--enable", action="store_true", help="Enable all AI image generation")
    parser.add_argument("--hero-only", action="store_true", help="Enable only hero images")
    parser.add_argument("--status", action="store_true", help="Show current status")
    
    args = parser.parse_args()
    
    # If no arguments, show status
    if not any([args.disable, args.enable, args.hero_only, args.status]):
        args.status = True
    
    if args.disable:
        disable_all()
        print_status()
    elif args.enable:
        enable_all()
        print_status()
    elif args.hero_only:
        enable_hero_only()
        print_status()
    elif args.status:
        print_status()

if __name__ == "__main__":
    main()
