#!/usr/bin/env python3
"""
Complete Enhanced System Test
Tests the full blog generation flow with enhanced image requirements.
"""

import os
import sys
import logging

# Set up Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bloggen.flows import BlogGenerationFlow
from bloggen.agent_factory import AgentFactory
from bloggen.task_factory import TaskFactory
from bloggen.tools_manager import ToolsManager

# Set up basic logging
logging.basicConfig(level=logging.WARNING)

def status_callback(step_name, progress, details):
    """Simple status callback for testing."""
    print(f"📊 {step_name}: {progress}% - {details}")

def test_complete_enhanced_system():
    """Test the complete enhanced system with mandatory 2-3 images."""
    print("🚀 TESTING COMPLETE ENHANCED SYSTEM")
    print("=" * 60)
    
    try:
        # Create flow instance
        flow = BlogGenerationFlow(
            topic="Sustainable Technology Innovations",
            current_year=2025,
            user_id=None,
            blog_id=None,
            instructions="Write about green technology trends with visual examples.",
            status_callback=status_callback,
            audit_tracker=None,  # Skip audit for test
        )
        
        print("✅ Flow created successfully")
        
        # Execute the flow (this will run all phases)
        result = flow.kickoff()
        
        print("\n🎯 SYSTEM RESULTS:")
        print("=" * 40)
        
        # Check final blog content
        final_blog = result.get('final_blog_post', '')
        
        if final_blog:
            print(f"📝 Blog length: {len(final_blog)} characters")
            
            # Count images in final blog
            image_count = final_blog.count('![')
            print(f"🖼️  Total images: {image_count}")
            
            # Check for proper Unsplash images
            unsplash_images = final_blog.count('images.unsplash.com')
            print(f"📸 Unsplash images: {unsplash_images}")
            
            # Check for deprecated sources
            deprecated_sources = final_blog.count('source.unsplash.com')
            if deprecated_sources > 0:
                print(f"⚠️  Deprecated sources found: {deprecated_sources}")
            else:
                print("✅ No deprecated image sources")
            
            # Success criteria
            success = True
            issues = []
            
            if image_count < 2:
                success = False
                issues.append(f"Insufficient images: {image_count} < 2")
            
            if deprecated_sources > 0:
                success = False
                issues.append(f"Deprecated sources found: {deprecated_sources}")
            
            if unsplash_images == 0:
                success = False
                issues.append("No Unsplash images found")
            
            print("\n🏆 FINAL ASSESSMENT:")
            if success:
                print("✅ COMPLETE ENHANCED SYSTEM WORKING PERFECTLY!")
                print("   • 2+ images generated")
                print("   • No deprecated sources")
                print("   • Proper tool usage")
            else:
                print("❌ ISSUES DETECTED:")
                for issue in issues:
                    print(f"   • {issue}")
                    
            return success
            
        else:
            print("❌ No final blog content generated")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_enhanced_system()
    if success:
        print("\n🎉 All systems operational!")
        sys.exit(0)
    else:
        print("\n💥 System needs attention!")
        sys.exit(1)
