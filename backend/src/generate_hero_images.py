#!/usr/bin/env python3
"""
Hero Image Generation Utility

This utility generates hero images for existing blogs in the database that don't have them.
It uses the same OpenAI image generation logic as the main blog generation flow.

Usage:
    python generate_hero_images.py [--dry-run] [--force] [--limit N]
    
Options:
    --dry-run    Show what would be done without making changes
    --force      Regenerate images even for blogs that already have them  
    --limit N    Only process N blogs (useful for testing)
"""

import asyncio
import asyncpg
import os
import sys
import argparse
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
load_dotenv(os.path.join(backend_dir, '.env'))

# Add src to path so we can import our modules
sys.path.insert(0, script_dir)

from bloggen.tools.openai_image_tool import OpenAIImageTool
from bloggen.tools.unsplash_tool import UnsplashImageTool
from core.config import config


class HeroImageGenerator:
    """Generates hero images for existing blogs in the database."""
    
    def __init__(self, dry_run: bool = False, force: bool = False):
        self.dry_run = dry_run
        self.force = force
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        self.skipped_count = 0
        
    async def connect_db(self) -> asyncpg.Connection:
        """Connect to the database."""
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        # Disable statement cache to avoid conflicts with main app
        return await asyncpg.connect(database_url, statement_cache_size=0)
    
    def extract_url_from_markdown(self, markdown_text: str) -> Optional[str]:
        """Extract URL from markdown format: ![alt](url "caption")"""
        if isinstance(markdown_text, str):
            url_match = re.search(r'!\[.*?\]\((.*?)\s*(?:\".*?\")?\)', markdown_text)
            return url_match.group(1) if url_match else None
        return None
    
    async def generate_hero_image(self, topic: str, blog_id: str) -> Optional[str]:
        """Generate a hero image for the given topic."""
        try:
            print(f"  🎨 Generating hero image for topic: '{topic}'")
            
            # Check if AI image generation is enabled
            if not config.features.enable_hero_image_generation:
                print(f"  ⚠️  AI image generation is disabled - skipping")
                return None
            
            # Generate image using OpenAI
            prompt = f"Photorealistic, high-quality professional image directly representing '{topic}'. Modern, stylish composition with excellent lighting, sharp focus, and cinematic quality. Suitable for premium blog header, visually striking and directly relevant to the topic."
            
            hero_tool = OpenAIImageTool()
            hero_result = hero_tool.run(prompt)
            
            hero_url = None
            if isinstance(hero_result, str):
                hero_url = self.extract_url_from_markdown(hero_result)
                print(f"  ✅ OpenAI generated image: {hero_url[:80]}..." if hero_url else "  ❌ Failed to extract URL from OpenAI result")
            elif isinstance(hero_result, dict):
                hero_url = hero_result.get('url')
                print(f"  ✅ OpenAI generated image: {hero_url[:80]}..." if hero_url else "  ❌ No URL in OpenAI result dict")
            
            # Fallback to Unsplash if OpenAI failed or returned placeholder
            if not hero_url or 'placeholder' in (hero_url or '') or 'placehold.co' in (hero_url or ''):
                print(f"  🔄 Falling back to Unsplash for topic: '{topic}'")
                try:
                    unsplash_tool = UnsplashImageTool()
                    unsplash_res = unsplash_tool.run(topic)
                    if isinstance(unsplash_res, dict):
                        hero_url = unsplash_res.get('url') or hero_url
                        print(f"  ✅ Unsplash generated image: {hero_url[:80]}..." if hero_url else "  ❌ Unsplash also failed")
                except Exception as e:
                    print(f"  ❌ Unsplash fallback failed: {e}")
            
            return hero_url
            
        except Exception as e:
            print(f"  ❌ Error generating hero image: {e}")
            return None
    
    async def update_blog_hero_image(self, conn: asyncpg.Connection, blog_id: str, hero_url: str) -> bool:
        """Update the hero image URL in the database."""
        try:
            if self.dry_run:
                print(f"  🚫 DRY RUN: Would update blog {blog_id} with hero URL: {hero_url[:80]}...")
                return True
            
            await conn.execute(
                "UPDATE blogs SET hero_image_url = $1, updated_at = $2 WHERE id = $3",
                hero_url, datetime.utcnow(), blog_id
            )
            print(f"  ✅ Updated database with hero URL: {hero_url[:80]}...")
            return True
            
        except Exception as e:
            print(f"  ❌ Error updating database: {e}")
            return False
    
    async def get_blogs_to_process(self, conn: asyncpg.Connection, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get blogs that need hero image generation."""
        
        if self.force:
            # Process all blogs if force flag is set
            condition = "TRUE"
            print("🔄 Force mode: Processing ALL blogs regardless of existing hero images")
        else:
            # Only process blogs without hero images
            condition = "(hero_image_url IS NULL OR hero_image_url = '')"
            print("🎯 Normal mode: Processing only blogs without hero images")
        
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f"""
            SELECT id, topic, hero_image_url, created_at 
            FROM blogs 
            WHERE {condition}
            ORDER BY created_at DESC 
            {limit_clause}
        """
        
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]
    
    async def process_blogs(self, limit: Optional[int] = None):
        """Main processing function."""
        print("🚀 Starting Hero Image Generation Utility")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print(f"Force regeneration: {'YES' if self.force else 'NO'}")
        print(f"AI Image Generation Enabled: {config.features.enable_hero_image_generation}")
        print("-" * 70)
        
        conn = await self.connect_db()
        try:
            blogs = await self.get_blogs_to_process(conn, limit)
            print(f"📊 Found {len(blogs)} blogs to process")
            print("-" * 70)
            
            if not blogs:
                print("✅ No blogs need hero image generation!")
                return
            
            for i, blog in enumerate(blogs, 1):
                blog_id = blog['id']
                topic = blog['topic'] or 'AI Blog'
                existing_url = blog['hero_image_url']
                created_at = blog['created_at']
                
                print(f"\n📝 Processing blog {i}/{len(blogs)}")
                print(f"  ID: {blog_id}")
                print(f"  Topic: {topic}")
                print(f"  Created: {created_at}")
                print(f"  Existing hero URL: {existing_url or 'None'}")
                
                self.processed_count += 1
                
                if existing_url and not self.force:
                    print(f"  ⏭️  Skipping - already has hero image")
                    self.skipped_count += 1
                    continue
                
                # Generate hero image
                hero_url = await self.generate_hero_image(topic, blog_id)
                
                if hero_url:
                    # Update database
                    success = await self.update_blog_hero_image(conn, blog_id, hero_url)
                    if success:
                        self.success_count += 1
                        print(f"  🎉 SUCCESS: Generated and saved hero image")
                    else:
                        self.error_count += 1
                        print(f"  💥 ERROR: Generated image but failed to save to database")
                else:
                    self.error_count += 1
                    print(f"  💥 ERROR: Failed to generate hero image")
                
                # Small delay to be respectful to APIs
                await asyncio.sleep(1)
        
        finally:
            await conn.close()
    
    def print_summary(self):
        """Print processing summary."""
        print("\n" + "=" * 70)
        print("📊 HERO IMAGE GENERATION SUMMARY")
        print("=" * 70)
        print(f"Total blogs processed: {self.processed_count}")
        print(f"✅ Successfully generated: {self.success_count}")
        print(f"💥 Errors: {self.error_count}")
        print(f"⏭️  Skipped (already had images): {self.skipped_count}")
        print(f"Mode: {'DRY RUN - No changes made' if self.dry_run else 'LIVE - Changes saved to database'}")
        print("=" * 70)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate hero images for existing blogs in the database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python generate_hero_images.py                    # Process all blogs without hero images
  python generate_hero_images.py --dry-run          # Show what would be done without changes
  python generate_hero_images.py --force            # Regenerate ALL blog hero images
  python generate_hero_images.py --limit 5          # Process only 5 blogs for testing
  python generate_hero_images.py --dry-run --limit 3  # Test mode: show what would be done for 3 blogs
        """
    )
    
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be done without making any changes'
    )
    
    parser.add_argument(
        '--force', 
        action='store_true',
        help='Regenerate images even for blogs that already have them'
    )
    
    parser.add_argument(
        '--limit', 
        type=int, 
        metavar='N',
        help='Only process N blogs (useful for testing)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.limit and args.limit <= 0:
        print("Error: --limit must be a positive number")
        sys.exit(1)
    
    try:
        generator = HeroImageGenerator(dry_run=args.dry_run, force=args.force)
        await generator.process_blogs(limit=args.limit)
        generator.print_summary()
        
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
