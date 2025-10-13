#!/usr/bin/env python3
"""
Quarterly Orphaned S3 Image Cleanup Utility

This utility identifies and removes orphaned S3 images that no longer
have corresponding blog records in the database. Designed to run every 3 months.

Usage:
    python src/utils/cleanup_orphaned_images.py --dry-run
    python src/utils/cleanup_orphaned_images.py --force
    python src/utils/cleanup_orphaned_images.py --cost-analysis
"""

import asyncio
import argparse
import sys
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple, Any
import logging

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.s3_storage import get_s3_storage
from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('orphaned_cleanup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class OrphanedImageCleaner:
    """
    Identifies and cleans up orphaned S3 images that no longer have
    corresponding blog records in the database.
    """
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.s3_storage = get_s3_storage()
        
    async def get_database_blog_ids(self) -> Set[str]:
        """Get all blog IDs from the database"""
        try:
            from core.task_manager import TaskManager
            
            task_manager = TaskManager()
            pool = await task_manager._get_db_connection()
            
            async with pool.acquire() as conn:
                # Get all blog IDs from database
                rows = await conn.fetch("SELECT id FROM blogs")
                blog_ids = {row['id'] for row in rows}
                
            logger.info(f"Found {len(blog_ids)} blogs in database")
            return blog_ids
            
        except Exception as e:
            logger.error(f"Failed to get blog IDs from database: {e}")
            return set()
    
    async def get_s3_image_info(self) -> List[Dict[str, Any]]:
        """Get information about all S3 images"""
        try:
            images = []
            
            # List all objects in the hero-images folder
            paginator = self.s3_storage.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.s3_storage.bucket_name,
                Prefix="hero-images/"
            )
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        size = obj['Size']
                        last_modified = obj['LastModified']
                        
                        # Extract blog ID from filename (format: hero-images/{blog_id}-{random}.jpg)
                        blog_id = self.extract_blog_id_from_key(key)
                        
                        images.append({
                            'key': key,
                            'blog_id': blog_id,
                            'size': size,
                            'last_modified': last_modified,
                            'url': f"https://{self.s3_storage.bucket_name}.s3.{self.s3_storage.region}.amazonaws.com/{key}"
                        })
            
            logger.info(f"Found {len(images)} S3 images")
            return images
            
        except Exception as e:
            logger.error(f"Failed to get S3 image information: {e}")
            return []
    
    def extract_blog_id_from_key(self, key: str) -> str | None:
        """Extract blog ID from S3 object key"""
        try:
            # Pattern: hero-images/{blog_id}-{random_chars}.jpg
            # Also handle: hero-images/temp-{hash}-{random_chars}.jpg
            
            filename = key.replace('hero-images/', '')
            
            # Skip temp files (these are content images without specific blog association)
            if filename.startswith('temp-'):
                return 'temp'
            
            # Extract blog ID (everything before the last dash)
            parts = filename.split('-')
            if len(parts) >= 2:
                # Rejoin all parts except the last one (which is the random suffix)
                blog_id = '-'.join(parts[:-1])
                return blog_id
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract blog ID from key {key}: {e}")
            return None
    
    async def identify_orphaned_images(self) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Identify orphaned images and return analysis"""
        logger.info("🔍 Identifying orphaned S3 images...")
        
        # Get database blog IDs and S3 images
        database_blog_ids = await self.get_database_blog_ids()
        s3_images = await self.get_s3_image_info()
        
        orphaned_images = []
        total_orphaned_size = 0
        
        # Categorize images
        by_category = {
            'has_blog': [],
            'orphaned': [],
            'temp_files': [],
            'invalid': []
        }
        
        for image in s3_images:
            blog_id = image['blog_id']
            
            if blog_id == 'temp':
                by_category['temp_files'].append(image)
            elif blog_id is None:
                by_category['invalid'].append(image)
            elif blog_id not in database_blog_ids:
                by_category['orphaned'].append(image)
                orphaned_images.append(image)
                total_orphaned_size += image['size']
            else:
                by_category['has_blog'].append(image)
        
        # Calculate storage costs
        total_orphaned_gb = total_orphaned_size / (1024**3)
        monthly_cost = total_orphaned_gb * 0.023  # S3 Standard storage pricing
        annual_cost = monthly_cost * 12
        
        analysis = {
            'total_images': len(s3_images),
            'orphaned_count': len(orphaned_images),
            'orphaned_size_bytes': total_orphaned_size,
            'orphaned_size_gb': total_orphaned_gb,
            'monthly_cost': monthly_cost,
            'annual_cost': annual_cost,
            'categories': {k: len(v) for k, v in by_category.items()},
            'oldest_orphan': None,
            'newest_orphan': None
        }
        
        # Find oldest and newest orphaned images
        if orphaned_images:
            orphaned_images.sort(key=lambda x: x['last_modified'])
            analysis['oldest_orphan'] = orphaned_images[0]['last_modified']
            analysis['newest_orphan'] = orphaned_images[-1]['last_modified']
        
        return orphaned_images, analysis
    
    async def cleanup_orphaned_images(self, orphaned_images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Clean up orphaned images (with dry-run support)"""
        if not orphaned_images:
            logger.info("✅ No orphaned images found")
            return {'deleted': 0, 'failed': 0, 'savings': 0}
        
        logger.info(f"🧹 {'DRY RUN: Would delete' if self.dry_run else 'Deleting'} {len(orphaned_images)} orphaned images")
        
        deleted_count = 0
        failed_count = 0
        total_savings = 0
        
        if not self.dry_run:
            # Batch delete for efficiency
            batch_size = 1000
            for i in range(0, len(orphaned_images), batch_size):
                batch = orphaned_images[i:i + batch_size]
                
                try:
                    # Prepare delete objects request
                    delete_objects = [{'Key': img['key']} for img in batch]
                    
                    response = self.s3_storage.s3_client.delete_objects(
                        Bucket=self.s3_storage.bucket_name,
                        Delete={'Objects': delete_objects}
                    )
                    
                    # Count successful deletions
                    if 'Deleted' in response:
                        batch_deleted = len(response['Deleted'])
                        deleted_count += batch_deleted
                        
                        # Calculate savings for this batch
                        batch_size_bytes = sum(img['size'] for img in batch[:batch_deleted])
                        batch_gb = batch_size_bytes / (1024**3)
                        total_savings += batch_gb * 0.023  # Monthly savings
                    
                    # Track any errors
                    if 'Errors' in response:
                        failed_count += len(response['Errors'])
                        for error in response['Errors']:
                            logger.error(f"Failed to delete {error['Key']}: {error['Message']}")
                
                except Exception as e:
                    logger.error(f"Batch delete failed: {e}")
                    failed_count += len(batch)
        else:
            # Dry run - just calculate what would be saved
            deleted_count = len(orphaned_images)
            total_size_bytes = sum(img['size'] for img in orphaned_images)
            total_gb = total_size_bytes / (1024**3)
            total_savings = total_gb * 0.023
        
        return {
            'deleted': deleted_count,
            'failed': failed_count,
            'monthly_savings': total_savings,
            'annual_savings': total_savings * 12
        }
    
    async def generate_report(self, analysis: Dict[str, Any], cleanup_result: Dict[str, Any]):
        """Generate comprehensive cleanup report"""
        print("\n" + "="*70)
        print("📊 QUARTERLY S3 ORPHANED IMAGE CLEANUP REPORT")
        print("="*70)
        print(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE CLEANUP'}")
        print()
        
        print("📈 STORAGE ANALYSIS:")
        print(f"   Total S3 images: {analysis['total_images']:,}")
        print(f"   Images with valid blogs: {analysis['categories']['has_blog']:,}")
        print(f"   Orphaned images: {analysis['categories']['orphaned']:,}")
        print(f"   Temp/content images: {analysis['categories']['temp_files']:,}")
        print(f"   Invalid/unclassified: {analysis['categories']['invalid']:,}")
        print()
        
        if analysis['orphaned_count'] > 0:
            print("🗑️  ORPHANED IMAGE DETAILS:")
            print(f"   Count: {analysis['orphaned_count']:,}")
            print(f"   Total size: {analysis['orphaned_size_gb']:.4f} GB")
            print(f"   Monthly cost: ${analysis['monthly_cost']:.6f}")
            print(f"   Annual cost: ${analysis['annual_cost']:.4f}")
            
            if analysis['oldest_orphan']:
                print(f"   Oldest orphan: {analysis['oldest_orphan'].strftime('%Y-%m-%d')}")
            if analysis['newest_orphan']:
                print(f"   Newest orphan: {analysis['newest_orphan'].strftime('%Y-%m-%d')}")
            print()
        
        print("🧹 CLEANUP RESULTS:")
        print(f"   Images {'would be ' if self.dry_run else ''}deleted: {cleanup_result['deleted']:,}")
        if cleanup_result['failed'] > 0:
            print(f"   Failed deletions: {cleanup_result['failed']:,}")
        print(f"   Monthly savings: ${cleanup_result['monthly_savings']:.6f}")
        print(f"   Annual savings: ${cleanup_result['annual_savings']:.4f}")
        print()
        
        if self.dry_run:
            print("💡 RECOMMENDATIONS:")
            if analysis['orphaned_count'] > 0:
                print(f"   Run with --force to delete {analysis['orphaned_count']} orphaned images")
                print(f"   This would save ~${cleanup_result['annual_savings']:.2f} annually")
            else:
                print("   No action needed - no orphaned images found")
            print("   Schedule this script to run quarterly for optimal cost management")
        else:
            print("✅ CLEANUP COMPLETED!")
            if cleanup_result['deleted'] > 0:
                print(f"   Successfully cleaned up {cleanup_result['deleted']} orphaned images")
                print(f"   Ongoing annual savings: ${cleanup_result['annual_savings']:.2f}")
        
        print("="*70)
    
    async def run_cleanup(self):
        """Run the complete orphaned image cleanup process"""
        try:
            # Start audit session for tracking
            async with EnhancedDatabaseAuditTracker('quarterly_cleanup', user_id='system') as tracker:
                
                # Identify orphaned images
                orphaned_images, analysis = await self.identify_orphaned_images()
                
                # Perform cleanup
                cleanup_result = await self.cleanup_orphaned_images(orphaned_images)
                
                # Track in audit system
                if cleanup_result['deleted'] > 0:
                    tracker.track_storage_cleanup(
                        blog_id='quarterly_cleanup',
                        images_deleted=cleanup_result['deleted'],
                        estimated_storage_gb=analysis['orphaned_size_gb'],
                        monthly_savings=cleanup_result['monthly_savings'],
                        status='success' if cleanup_result['failed'] == 0 else 'partial'
                    )
                
                # Generate report
                await self.generate_report(analysis, cleanup_result)
                
                return cleanup_result
                
        except Exception as e:
            logger.error(f"Orphaned image cleanup failed: {e}")
            raise


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Quarterly S3 Orphaned Image Cleanup')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('--force', action='store_true',
                       help='Actually delete orphaned images')
    parser.add_argument('--cost-analysis', action='store_true',
                       help='Show cost analysis only (same as --dry-run)')
    
    args = parser.parse_args()
    
    # Default to dry run if no mode specified
    if not args.force:
        dry_run = True
    else:
        dry_run = False
    
    if args.cost_analysis:
        dry_run = True
    
    print(f"🚀 Starting Quarterly S3 Orphaned Image Cleanup")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE CLEANUP'}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    try:
        cleaner = OrphanedImageCleaner(dry_run=dry_run)
        result = await cleaner.run_cleanup()
        
        if dry_run and not args.cost_analysis:
            print("\n💡 To perform actual cleanup, run with --force flag")
        
        return 0
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
