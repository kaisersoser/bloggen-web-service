#!/usr/bin/env python3
"""
Test script for enhanced image integration in blog generation.
"""
import sys
import os
sys.path.append('src')

import asyncio
from bloggen.flows import BlogGenerationFlow
from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker

async def test_enhanced_image_flow():
    """Test the enhanced blog generation flow with parallel images."""
    
    print("🚀 Testing Enhanced Image Integration Flow")
    
    # Create audit tracker
    audit_tracker = EnhancedDatabaseAuditTracker(
        session_type="test",
        user_id="test_user",
        blog_id="test_blog_enhanced_images"
    )
    
    try:
        await audit_tracker.start_session()
        
        # Create flow with enhanced image capabilities
        flow = BlogGenerationFlow(
            audit_tracker=audit_tracker,
            user_id="test_user",
            blog_id="test_blog_enhanced_images"
        )
        
        # Test with a simple AI topic
        print("📝 Generating blog about 'AI automation tools for 2025'...")
        
        result = flow.kickoff(
            inputs={
                "topic": "AI automation tools for 2025",
                "current_year": 2025,
                "instructions": "Focus on practical tools and include specific examples"
            }
        )
        
        print(f"\n✅ Blog generation completed!")
        print(f"📊 Result type: {type(result)}")
        
        if hasattr(result, 'final_blog_post'):
            final_content = result.final_blog_post
        elif isinstance(result, dict) and 'final_blog_post' in result:
            final_content = result['final_blog_post']
        else:
            final_content = str(result)
        
        # Check for image integration
        unsplash_images = final_content.count("images.unsplash.com")
        openai_images = final_content.count("oaidalleapiprodscus.blob.core.windows.net")
        deprecated_images = final_content.count("source.unsplash.com")
        
        print(f"\n📈 Image Integration Analysis:")
        print(f"  - Unsplash API images: {unsplash_images}")
        print(f"  - OpenAI generated images: {openai_images}")
        print(f"  - Deprecated image sources: {deprecated_images}")
        print(f"  - Total proper images: {unsplash_images + openai_images}")
        
        # Save result for inspection
        with open("enhanced_blog_test_result.md", "w") as f:
            f.write(final_content)
        print(f"\n📄 Full blog saved to: enhanced_blog_test_result.md")
        
        # Check audit tracking
        summary = audit_tracker.get_session_summary()
        print(f"\n💰 Cost Summary: ${summary.get('total_cost', 0):.4f}")
        print(f"🔄 API Calls: {summary.get('total_calls', 0)}")
        
        return final_content
        
    finally:
        await audit_tracker.end_session()

if __name__ == "__main__":
    asyncio.run(test_enhanced_image_flow())
