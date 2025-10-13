#!/usr/bin/env python3
# flake8: noqa
"""
Debug script to analyze what logging output image tools actually produce.
"""

import sys
import os
import logging
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bloggen.tools.unsplash_tool import UnsplashImageTool
from bloggen.tools.openai_image_tool import OpenAIImageTool


class LoggingInterceptor(logging.Handler):
    """Custom logging handler to intercept and analyze logging output"""

    def __init__(self):
        super().__init__()
        self.captured_logs: List[Dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Capture logging records"""
        message = self.format(record)
        self.captured_logs.append(
            {
                "level": record.levelname,
                "logger": record.name,
                "message": message,
                "module": record.module,
                "funcName": record.funcName,
            }
        )
        print(f"📋 CAPTURED LOG: [{record.levelname}] {record.name}: {message}")


def test_image_tool_logging():
    """Test what logging output image tools actually produce"""
    print("🔍 ANALYZING IMAGE TOOL LOGGING OUTPUT")
    print("=" * 50)

    # Set up logging interceptor
    interceptor = LoggingInterceptor()

    # Add handler to root logger and tool-specific loggers
    loggers_to_monitor = [
        logging.getLogger(),  # Root logger
        logging.getLogger("bloggen.tools.unsplash_tool"),
        logging.getLogger("bloggen.tools.openai_image_tool"),
        logging.getLogger("root"),
    ]

    for logger in loggers_to_monitor:
        logger.addHandler(interceptor)
        logger.setLevel(logging.DEBUG)

    print("\n🖼️  TESTING UNSPLASH TOOL...")
    try:
        unsplash_tool = UnsplashImageTool()
        result = unsplash_tool._run("machine learning algorithm", count=1)
        print(f"✅ Unsplash result: {result[:100]}...")
    except Exception as e:
        print(f"❌ Unsplash error: {e}")

    print(f"\n📊 Unsplash logs captured: {len(interceptor.captured_logs)}")
    for i, log in enumerate(interceptor.captured_logs, 1):
        print(f"  {i}. [{log['level']}] {log['logger']}: {log['message']}")

    # Clear logs for next test
    interceptor.captured_logs.clear()

    print("\n🎨 TESTING OPENAI TOOL...")
    try:
        openai_tool = OpenAIImageTool()
        result = openai_tool._run("futuristic robot assistant")
        print(f"✅ OpenAI result: {result[:100]}...")
    except Exception as e:
        print(f"❌ OpenAI error: {e}")

    print(f"\n📊 OpenAI logs captured: {len(interceptor.captured_logs)}")
    for i, log in enumerate(interceptor.captured_logs, 1):
        print(f"  {i}. [{log['level']}] {log['logger']}: {log['message']}")

    # Clean up handlers
    for logger in loggers_to_monitor:
        logger.removeHandler(interceptor)

    return interceptor.captured_logs


def analyze_image_patterns(logs: List[Dict[str, Any]]):
    """Analyze what patterns we should look for in image tool logs"""
    print(f"\n🔍 ANALYZING PATTERNS IN {len(logs)} LOG MESSAGES")
    print("=" * 50)

    image_keywords = [
        "image",
        "unsplash",
        "openai",
        "dall-e",
        "photo",
        "picture",
        "visual",
        "generate",
        "search",
        "api",
        "url",
        "fallback",
        "generation",
        "placeholder",
        "s3",
        "storage",
    ]

    relevant_logs = []
    for log in logs:
        message_lower = log["message"].lower()
        if any(keyword in message_lower for keyword in image_keywords):
            relevant_logs.append(log)

    print(f"📋 Relevant image-related logs: {len(relevant_logs)}")
    for i, log in enumerate(relevant_logs, 1):
        print(f"  {i}. [{log['level']}] {log['message']}")

    # Suggest regex patterns
    print(f"\n💡 SUGGESTED REGEX PATTERNS:")
    pattern_suggestions = [
        r"Unsplash tool initialized with API key",
        r"Searching Unsplash for:",
        r"Successfully found \d+ relevant Unsplash images",
        r"falling back to AI generation",
        r"Generated AI image \d+",
        r"Image stored permanently in S3:",
        r"using placeholder",
    ]

    for pattern in pattern_suggestions:
        print(f"    '{pattern}'")


if __name__ == "__main__":
    captured_logs = test_image_tool_logging()
    analyze_image_patterns(captured_logs)
