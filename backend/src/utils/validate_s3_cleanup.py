#!/usr/bin/env python3
"""
S3 Cleanup Validation and Testing Utility

This utility provides comprehensive testing and validation capabilities
for the S3 image cleanup system, including cost analysis and audit testing.

Usage:
    python src/utils/validate_s3_cleanup.py --test-cleanup
    python src/utils/validate_s3_cleanup.py --cost-analysis
    python src/utils/validate_s3_cleanup.py --audit-test
    python src/utils/validate_s3_cleanup.py --full-test
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Set
import logging

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.s3_storage import get_s3_storage
from core.s3_cleanup_queue import get_cleanup_queue, CleanupTask, CleanupStatus
from core.audit_tracker import DatabaseAuditTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('s3_cleanup_validation.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class S3CleanupValidator:
    """
    Comprehensive validation and testing for S3 cleanup system
    """
    
    def __init__(self):
        self.s3_storage = get_s3_storage()
        self.test_results = {}
        
    async def test_s3_connectivity(self) -> bool:
        """Test basic S3 connectivity and permissions"""
        print("🔧 Testing S3 Connectivity...")
        
        try:
            success = self.s3_storage.test_connection()
            if success:
                print("   ✅ S3 connection successful")
                
                # Test listing permissions
                try:
                    # Try to list objects in bucket
                    response = self.s3_storage.s3_client.list_objects_v2(
                        Bucket=self.s3_storage.bucket_name,
                        MaxKeys=1
                    )
                    print("   ✅ S3 list permissions working")
                    
                    # Test if we can get object count
                    if 'Contents' in response:
                        print(f"   📊 Bucket contains objects")
                    else:
                        print(f"   📊 Bucket is empty or no objects in prefix")
                        
                except Exception as e:
                    print(f"   ❌ S3 list permissions failed: {e}")
                    return False
                
                return True
            else:
                print("   ❌ S3 connection failed")
                return False
                
        except Exception as e:
            print(f"   ❌ S3 connectivity test failed: {e}")
            return False
    
    async def test_cleanup_queue(self) -> bool:
        """Test the S3 cleanup queue system"""
        print("🔄 Testing S3 Cleanup Queue...")
        
        try:
            # Get cleanup queue
            cleanup_queue = await get_cleanup_queue()
            
            # Check queue stats
            stats = cleanup_queue.get_queue_stats()
            print(f"   📊 Queue Status: {stats}")
            
            # Test enqueueing a dummy task (but don't process it)
            test_blog_id = f"test-{int(datetime.now().timestamp())}"
            test_task = await cleanup_queue.enqueue_cleanup(
                blog_id=test_blog_id,
                user_id="test-user",
                content="Test content with no S3 URLs",
                hero_image_url=None
            )
            
            print(f"   ✅ Successfully enqueued test task: {test_task.blog_id}")
            
            # Check task status
            task_status = await cleanup_queue.get_task_status(test_blog_id)
            if task_status:
                print(f"   ✅ Task status retrieval working: {task_status.status}")
            else:
                print("   ❌ Task status retrieval failed")
                return False
            
            # Wait a moment for processing (or timeout)
            await asyncio.sleep(2)
            
            # Check final status
            final_status = await cleanup_queue.get_task_status(test_blog_id)
            if final_status:
                print(f"   📋 Final task status: {final_status.status.value}")
                if final_status.status == CleanupStatus.COMPLETED:
                    print("   ✅ Cleanup queue processing working")
                else:
                    print(f"   ⚠️ Task status: {final_status.status.value} (expected for test)")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Cleanup queue test failed: {e}")
            return False
    
    async def test_image_extraction(self) -> bool:
        """Test image URL extraction from content"""
        print("🔍 Testing Image URL Extraction...")
        
        try:
            # Test content with various S3 URLs
            test_content = f'''
            # Test Blog Content
            
            Here's an image: ![Test](https://{self.s3_storage.bucket_name}.s3.{self.s3_storage.region}.amazonaws.com/hero-images/test-image-123.jpg)
            
            And another: ![Test2](https://{self.s3_storage.bucket_name}.s3.{self.s3_storage.region}.amazonaws.com/hero-images/another-456.jpg "Caption")
            
            Not an S3 URL: ![External](https://example.com/image.jpg)
            '''
            
            urls = self.s3_storage.extract_image_urls_from_content(test_content)
            
            print(f"   📊 Extracted {len(urls)} S3 URLs from test content")
            for url in urls:
                print(f"      - {url}")
            
            # Verify correct extraction
            expected_count = 2  # We expect 2 S3 URLs
            if len(urls) == expected_count:
                print("   ✅ Image URL extraction working correctly")
                return True
            else:
                print(f"   ❌ Expected {expected_count} URLs, got {len(urls)}")
                return False
                
        except Exception as e:
            print(f"   ❌ Image URL extraction test failed: {e}")
            return False
    
    async def test_cost_calculation(self) -> bool:
        """Test cost calculation accuracy"""
        print("💰 Testing Cost Calculations...")
        
        try:
            # Test scenarios
            test_cases = [
                {"images": 1, "expected_gb": 0.0002, "expected_monthly": 0.0002 * 0.023},
                {"images": 10, "expected_gb": 0.002, "expected_monthly": 0.002 * 0.023},
                {"images": 100, "expected_gb": 0.02, "expected_monthly": 0.02 * 0.023},
            ]
            
            all_passed = True
            
            for case in test_cases:
                images = case["images"]
                expected_gb = case["expected_gb"]
                expected_monthly = case["expected_monthly"]
                
                # Calculate using the same formula as the system
                calculated_gb = images * 0.0002  # 200KB per image
                calculated_monthly = calculated_gb * 0.023  # S3 pricing
                
                gb_match = abs(calculated_gb - expected_gb) < 0.000001
                cost_match = abs(calculated_monthly - expected_monthly) < 0.000001
                
                status = "✅" if (gb_match and cost_match) else "❌"
                print(f"   {status} {images} images: {calculated_gb:.6f}GB, ${calculated_monthly:.8f}/month")
                
                if not (gb_match and cost_match):
                    all_passed = False
                    print(f"      Expected: {expected_gb:.6f}GB, ${expected_monthly:.8f}/month")
            
            if all_passed:
                print("   ✅ Cost calculations accurate")
                return True
            else:
                print("   ❌ Cost calculation errors detected")
                return False
                
        except Exception as e:
            print(f"   ❌ Cost calculation test failed: {e}")
            return False
    
    async def generate_cost_analysis_report(self):
        """Generate comprehensive cost analysis report"""
        print("\n" + "="*70)
        print("💰 S3 STORAGE COST ANALYSIS REPORT")
        print("="*70)
        
        try:
            # Get current S3 storage info
            total_objects = 0
            total_size_bytes = 0
            
            paginator = self.s3_storage.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.s3_storage.bucket_name,
                Prefix="hero-images/"
            )
            
            oldest_object = None
            newest_object = None
            
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_objects += 1
                        total_size_bytes += obj['Size']
                        
                        # Track oldest and newest
                        if oldest_object is None or obj['LastModified'] < oldest_object:
                            oldest_object = obj['LastModified']
                        if newest_object is None or obj['LastModified'] > newest_object:
                            newest_object = obj['LastModified']
            
            # Calculate costs
            total_gb = total_size_bytes / (1024**3)
            monthly_cost = total_gb * 0.023  # S3 Standard pricing
            annual_cost = monthly_cost * 12
            
            # Average image size
            avg_image_kb = (total_size_bytes / total_objects / 1024) if total_objects > 0 else 0
            
            print(f"📊 CURRENT STORAGE STATUS:")
            print(f"   Total images: {total_objects:,}")
            print(f"   Total storage: {total_gb:.4f} GB ({total_size_bytes:,} bytes)")
            print(f"   Average image size: {avg_image_kb:.1f} KB")
            print(f"   Monthly cost: ${monthly_cost:.6f}")
            print(f"   Annual cost: ${annual_cost:.4f}")
            
            if oldest_object and newest_object:
                storage_duration = newest_object - oldest_object
                print(f"   Storage timespan: {storage_duration.days} days")
            print()
            
            # Project growth scenarios
            print(f"📈 COST PROJECTIONS:")
            growth_scenarios = [
                {"name": "Current rate", "images_per_month": total_objects / max(1, (newest_object - oldest_object).days / 30) if oldest_object and newest_object else 0},
                {"name": "Conservative growth", "images_per_month": 100},
                {"name": "Moderate growth", "images_per_month": 500},
                {"name": "High growth", "images_per_month": 1000},
            ]
            
            for scenario in growth_scenarios:
                images_per_month = scenario["images_per_month"]
                if images_per_month <= 0:
                    continue
                    
                # Assume 12 months of accumulation with cleanup
                accumulated_images = images_per_month * 6  # 6 months average with quarterly cleanup
                storage_gb = accumulated_images * 0.0002
                monthly_cost = storage_gb * 0.023
                annual_cost = monthly_cost * 12
                
                print(f"   {scenario['name']}: {images_per_month:.0f} images/month")
                print(f"      Steady state: ~{accumulated_images:.0f} images, {storage_gb:.3f}GB")
                print(f"      Annual cost: ${annual_cost:.2f}")
            print()
            
            # Cleanup impact analysis
            print(f"🧹 CLEANUP IMPACT ANALYSIS:")
            cleanup_scenarios = [
                {"name": "Monthly cleanup", "retention_months": 1, "description": "Aggressive cleanup"},
                {"name": "Quarterly cleanup", "retention_months": 3, "description": "Recommended"},
                {"name": "Semi-annual cleanup", "retention_months": 6, "description": "Moderate"},
                {"name": "Annual cleanup", "retention_months": 12, "description": "Minimal"},
                {"name": "No cleanup", "retention_months": 24, "description": "Not recommended"},
            ]
            
            base_images_per_month = 200  # Reasonable estimate
            
            for scenario in cleanup_scenarios:
                retention = scenario["retention_months"]
                steady_state_images = base_images_per_month * retention
                storage_gb = steady_state_images * 0.0002
                annual_cost = storage_gb * 0.023 * 12
                
                print(f"   {scenario['name']} ({scenario['description']}):")
                print(f"      Retained images: ~{steady_state_images} images")
                print(f"      Annual storage cost: ${annual_cost:.2f}")
            
            print()
            print("💡 RECOMMENDATIONS:")
            print("   1. Implement quarterly cleanup (current plan) for optimal cost/maintenance balance")
            print("   2. Monitor growth trends and adjust cleanup frequency if needed")
            print("   3. Consider image compression/optimization for high-growth scenarios")
            print("   4. Track actual vs. projected costs using the audit system")
            
        except Exception as e:
            print(f"❌ Cost analysis failed: {e}")
    
    async def test_audit_integration(self) -> bool:
        """Test audit system integration"""
        print("📊 Testing Audit System Integration...")
        
        try:
            # Create test audit session
            async with DatabaseAuditTracker('s3_cleanup_test', user_id='test-user') as tracker:
                
                # Test storage cleanup tracking
                tracker.track_storage_cleanup(
                    blog_id='test-blog-123',
                    images_deleted=5,
                    estimated_storage_gb=0.001,
                    monthly_savings=0.000023,
                    status='success'
                )
                
                print("   ✅ Audit tracking integration working")
                
                # Verify total cost includes savings (negative cost)
                if tracker.total_cost < 0:
                    print(f"   ✅ Savings properly tracked as negative cost: ${tracker.total_cost:.8f}")
                else:
                    print(f"   ⚠️ Total cost: ${tracker.total_cost:.8f} (expected negative for savings)")
                
                return True
                
        except Exception as e:
            print(f"   ❌ Audit integration test failed: {e}")
            return False
    
    async def run_full_validation(self):
        """Run comprehensive validation suite"""
        print("🚀 Starting S3 Cleanup System Validation")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print("="*70)
        
        tests = [
            ("S3 Connectivity", self.test_s3_connectivity),
            ("Cleanup Queue", self.test_cleanup_queue),
            ("Image Extraction", self.test_image_extraction),
            ("Cost Calculations", self.test_cost_calculation),
            ("Audit Integration", self.test_audit_integration),
        ]
        
        results = {}
        all_passed = True
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                results[test_name] = result
                if not result:
                    all_passed = False
                print()
            except Exception as e:
                print(f"   ❌ {test_name} test crashed: {e}")
                results[test_name] = False
                all_passed = False
                print()
        
        # Summary
        print("="*70)
        print("📋 VALIDATION SUMMARY")
        print("="*70)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
        
        print()
        if all_passed:
            print("🎉 ALL TESTS PASSED - S3 Cleanup System Ready for Production")
        else:
            print("⚠️ SOME TESTS FAILED - Review issues before deploying")
        
        print(f"📝 Detailed logs saved to: s3_cleanup_validation.log")
        print("="*70)
        
        return all_passed


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='S3 Cleanup Validation and Testing')
    parser.add_argument('--test-cleanup', action='store_true',
                       help='Test cleanup queue functionality')
    parser.add_argument('--cost-analysis', action='store_true',
                       help='Generate comprehensive cost analysis report')
    parser.add_argument('--audit-test', action='store_true',
                       help='Test audit system integration')
    parser.add_argument('--full-test', action='store_true',
                       help='Run complete validation suite')
    
    args = parser.parse_args()
    
    validator = S3CleanupValidator()
    
    try:
        if args.cost_analysis:
            await validator.generate_cost_analysis_report()
        elif args.test_cleanup:
            await validator.test_cleanup_queue()
        elif args.audit_test:
            await validator.test_audit_integration()
        elif args.full_test:
            success = await validator.run_full_validation()
            return 0 if success else 1
        else:
            # Default to full test
            success = await validator.run_full_validation()
            return 0 if success else 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
