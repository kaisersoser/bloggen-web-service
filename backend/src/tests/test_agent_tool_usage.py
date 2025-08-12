#!/usr/bin/env python3
"""
Test to verify that agents actually call image tools during generation.
"""
import sys
import os
sys.path.append('src')

from bloggen.agent_factory import AgentFactory
from bloggen.task_factory import TaskFactory
from bloggen.tools_manager import ToolsManager
from crewai import Crew

def test_agent_tool_usage():
    """Test if agents actually call the image tools."""
    
    print("🧪 Testing Agent Tool Usage")
    
    # Create tools manager and get content tools
    tools_manager = ToolsManager()
    content_tools = tools_manager.get_content_tools()
    
    print(f"📦 Loaded {len(content_tools)} content tools:")
    for tool in content_tools:
        print(f"  - {tool.name}: {tool.__class__.__name__}")
    
    # Create agent with tools
    agent = AgentFactory.create_content_creator(content_tools)
    
    # Create a simple task that should force tool usage
    simple_task_description = """
    Create a short blog section about "DIY home tools" with exactly ONE image.
    
    MANDATORY: You MUST call the unsplash_image_search tool to get an image.
    DO NOT create any image URLs manually.
    DO NOT use source.unsplash.com or any other manual URLs.
    ONLY use the tool to generate the image.
    
    Expected output:
    - One paragraph about DIY tools
    - One image from the unsplash_image_search tool
    - Tool-generated markdown preserved exactly
    """
    
    from crewai import Task
    task = Task(
        description=simple_task_description,
        agent=agent,
        expected_output="A short paragraph with one properly tool-generated image"
    )
    
    print("🚀 Running test with enforced tool usage...")
    
    # Create and run crew
    crew = Crew(agents=[agent], tasks=[task], verbose=True)
    result = crew.kickoff()
    
    print(f"\n📊 Result:")
    print(f"Result type: {type(result)}")
    result_text = str(result)
    print(f"Result content: {result_text}")
    
    # Analyze result
    has_source_unsplash = "source.unsplash.com" in result_text
    has_images_unsplash = "images.unsplash.com" in result_text
    has_openai_images = "oaidalleapiprodscus.blob.core.windows.net" in result_text
    image_count = result_text.count("![")
    
    print(f"\n📈 Analysis:")
    print(f"  - Total images found: {image_count}")
    print(f"  - Deprecated source.unsplash.com: {has_source_unsplash}")
    print(f"  - Proper images.unsplash.com: {has_images_unsplash}")
    print(f"  - OpenAI images: {has_openai_images}")
    
    if has_source_unsplash:
        print("❌ FAIL: Agent used deprecated image source instead of tools")
    elif has_images_unsplash or has_openai_images:
        print("✅ SUCCESS: Agent used proper image tools")
    else:
        print("⚠️  UNCLEAR: No images generated or different source")
    
    return result_text

if __name__ == "__main__":
    test_agent_tool_usage()
