#!/usr/bin/env python3
# flake8: noqa
"""
Test blog generation flow execution directly
"""
import sys
import os

# Add backend to path
sys.path.insert(
    0, "/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src"
)

# Load environment variables
from dotenv import load_dotenv

load_dotenv("/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/.env")

import logging
from datetime import datetime

from bloggen.flows import BlogGenerationFlow

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_flow():
    """Test the blog generation flow execution"""
    print("🚀 Testing BlogGenerationFlow Execution...")

    try:
        # Create flow
        flow = BlogGenerationFlow(
            user_id="test_user",
            topic="The Future of AI in Healthcare",
            current_year=datetime.now().year,
        )

        print("✅ Flow initialized successfully")

        # Test flow execution
        print("🔬 Starting flow execution...")
        result = flow.kickoff(
            {
                "topic": "The Future of AI in Healthcare",
                "current_year": datetime.now().year,
            }
        )

        print("✅ Flow execution completed!")
        print(f"📄 Result type: {type(result)}")
        if hasattr(result, "raw"):
            print(f"📄 Result length: {len(str(result.raw))} characters")
            print(f"📄 Result preview: {str(result.raw)[:200]}...")
        else:
            print(f"📄 Result length: {len(str(result))} characters")
            print(f"📄 Result preview: {str(result)[:200]}...")

        return True

    except Exception as e:
        print(f"❌ Flow execution failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_flow()
    if success:
        print("\n🎉 Blog generation flow test PASSED!")
    else:
        print("\n💥 Blog generation flow test FAILED!")
