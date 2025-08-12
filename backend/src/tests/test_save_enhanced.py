#!/usr/bin/env python3
"""
Save the enhanced flow result to a file for inspection.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from bloggen.flows import BlogGenerationFlow
from bloggen.content_validator import ContentValidator

def test_and_save_enhanced_result():
    """Test enhanced flow and save result to file"""
    
    print("🧪 TESTING AND SAVING ENHANCED FLOW RESULT")
    print("=" * 60)
    
    # Create flow with specific parameters
    flow = BlogGenerationFlow(
        user_id="test_user_save",
        blog_id="test_blog_save", 
        topic="Best AI Tools for Content Creation in 2025",
        current_year=2025
    )
    
    try:
        print("🚀 Starting enhanced blog generation...")
        
        # Execute the flow (now with post-processing)
        result = flow.kickoff()
        
        # Save to file
        output_path = "/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/generated_blogs/enhanced_blog.md"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(str(result))
        
        print(f"✅ Enhanced blog saved to: {output_path}")
        print(f"📊 Content length: {len(str(result))} characters")
        
        # Validate the result
        validator = ContentValidator()
        validation_result = validator.validate_content(str(result))
        
        print(f"\n🖼️ FINAL IMAGE ANALYSIS:")
        print(f"   📸 Total Images: {validation_result['total_images']}")
        print(f"   ✅ Valid Images: {validation_result['valid_images']}")
        print(f"   ❌ Deprecated Images: {validation_result['deprecated_images']}")
        print(f"   🎯 Overall Valid: {validation_result['valid']}")
        
        if validation_result['issues']:
            print(f"\n🚨 ISSUES FOUND:")
            for i, issue in enumerate(validation_result['issues'], 1):
                print(f"   {i}. {issue}")
        else:
            print(f"\n✅ NO ISSUES FOUND!")
        
        return str(result), validation_result
        
    except Exception as e:
        print(f"❌ Flow execution failed: {e}")
        import traceback
        traceback.print_exc()
        return None, {}

if __name__ == "__main__":
    test_and_save_enhanced_result()
