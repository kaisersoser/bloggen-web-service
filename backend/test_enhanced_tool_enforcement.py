#!/usr/bin/env python3
"""
Test the enhanced tool enforcement by generating a simple blog
and checking if agents actually call the tools.
"""

import sys
import os
import json

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from bloggen.flows import BlogGenerationFlow
from bloggen.tool_enforcement_validator import create_tool_enforcement_validator
import logging

# Set up logging to see tool calls
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_tool_enforcement():
    """Test if agents properly use tools with enhanced enforcement"""
    print("🔍 TESTING ENHANCED TOOL ENFORCEMENT")
    print("=" * 60)
    
    # Create tool enforcement validator
    validator = create_tool_enforcement_validator()
    
    def status_callback(step_name, progress, details):
        print(f"📊 {step_name}: {progress}% - {details}")
    
    # Create flow
    flow = BlogGenerationFlow(
        status_callback=status_callback,
        topic="Quantum Computing Fundamentals",
        current_year=2025,
        instructions="Write a short blog about quantum computing. Include 2 images: one real photo and one AI-generated illustration."
    )
    
    try:
        # Run the flow
        print("\n🚀 Starting blog generation with enhanced tool enforcement...")
        result = flow.kickoff()
        
        print(f"\n📝 Generated blog length: {len(result)} characters")
        print("\n" + "="*60)
        print("GENERATED CONTENT PREVIEW:")
        print("="*60)
        print(result[:500] + "..." if len(result) > 500 else result)
        print("="*60)
        
        # Validate the content
        validation_result = validator.validate_content_images(result)
        
        print(f"\n🔍 VALIDATION RESULTS:")
        print(f"   Total images: {validation_result.total_images}")
        print(f"   Valid images: {validation_result.valid_images}")
        print(f"   Invalid images: {len(validation_result.invalid_images)}")
        print(f"   Is valid: {validation_result.is_valid}")
        
        if validation_result.errors:
            print(f"\n❌ ERRORS:")
            for error in validation_result.errors:
                print(f"   - {error}")
        
        # Show enforcement summary
        summary = validator.get_enforcement_summary()
        print(f"\n📊 TOOL ENFORCEMENT SUMMARY:")
        print(f"   Tool calls made: {summary['tool_calls_made']}")
        print(f"   Tools used: {summary['tools_used']}")
        print(f"   Images generated: {summary['images_generated']}")
        
        return validation_result.is_valid
        
    except Exception as e:
        print(f"❌ ERROR during blog generation: {e}")
        return False

if __name__ == "__main__":
    success = test_tool_enforcement()
    
    if success:
        print("\n✅ SUCCESS: Tool enforcement working correctly!")
    else:
        print("\n❌ FAILURE: Agents still not using tools properly")
