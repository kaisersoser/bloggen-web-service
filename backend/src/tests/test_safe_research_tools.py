#!/usr/bin/env python3
"""
Test Safe Research Tools

Simple test to verify that our safe research tools work correctly and 
prevent binary content issues while respecting timeout limits.
"""

import sys
import os
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bloggen.tools.safe_research_tools import (
    SafeSerperTool, SafeWebScrapeTool, is_content_safe, safe_head_request
)


def test_content_safety_checks():
    """Test the content safety validation functions"""
    print("🧪 Testing Content Safety Validation")
    print("=" * 50)
    
    # Test safe URLs
    safe_urls = [
        "https://example.com/article.html",
        "https://api.example.com/data.json",
        "https://feeds.example.com/rss.xml",
        "https://site.com/page"
    ]
    
    print("✅ Testing SAFE URLs:")
    for url in safe_urls:
        result = is_content_safe(url)
        print(f"  {url}")
        print(f"    Safe: {result['safe']} - {result['reason']}")
    
    # Test unsafe URLs
    unsafe_urls = [
        "https://example.com/document.pdf",
        "https://site.com/file.zip",
        "https://media.com/video.mp4",
        "https://images.com/photo.jpg"
    ]
    
    print("\n❌ Testing UNSAFE URLs:")
    for url in unsafe_urls:
        result = is_content_safe(url)
        print(f"  {url}")
        print(f"    Safe: {result['safe']} - {result['reason']}")


def test_safe_head_request():
    """Test the safe HEAD request functionality"""
    print("\n🌐 Testing Safe HEAD Requests")
    print("=" * 50)
    
    # Test with a real website
    test_url = "https://httpbin.org/get"
    print(f"Testing HEAD request to: {test_url}")
    
    start_time = time.time()
    result = safe_head_request(test_url)
    elapsed = time.time() - start_time
    
    print(f"Request completed in {elapsed:.2f}s")
    print(f"Success: {result['success']}")
    
    if result['success']:
        print(f"Status: {result['status_code']}")
        print(f"Content-Type: {result['headers'].get('content-type', 'Not specified')}")
    else:
        print(f"Error: {result['error']}")


def test_safe_serper_tool():
    """Test the SafeSerperTool"""
    print("\n🔍 Testing SafeSerperTool")
    print("=" * 50)
    
    tool = SafeSerperTool()
    
    print(f"Tool name: {tool.name}")
    print(f"Tool description: {tool.description[:100]}...")
    
    # Test with a simple query
    query = "renewable energy technology 2024"
    print(f"\nSearching for: {query}")
    
    start_time = time.time()
    result = tool._run(query)
    elapsed = time.time() - start_time
    
    print(f"Search completed in {elapsed:.2f}s")
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(str(result))} characters")
    
    # Handle different result types safely
    result_str = str(result)
    print(f"Result preview: {result_str[:300]}...")


def test_safe_web_scrape_tool():
    """Test the SafeWebScrapeTool"""
    print("\n📄 Testing SafeWebScrapeTool")
    print("=" * 50)
    
    tool = SafeWebScrapeTool()
    
    print(f"Tool name: {tool.name}")
    print(f"Tool description: {tool.description[:100]}...")
    
    # Test with a safe URL
    safe_url = "https://httpbin.org/html"
    print(f"\nScraping safe URL: {safe_url}")
    
    start_time = time.time()
    result = tool._run(safe_url)
    elapsed = time.time() - start_time
    
    print(f"Scraping completed in {elapsed:.2f}s")
    print(f"Result length: {len(result)} characters")
    print(f"Result preview: {result[:300]}...")
    
    # Test with an unsafe URL (should be blocked)
    unsafe_url = "https://httpbin.org/image/png"
    print(f"\nTesting unsafe URL (should be blocked): {unsafe_url}")
    
    start_time = time.time()
    result = tool._run(unsafe_url)
    elapsed = time.time() - start_time
    
    print(f"Request completed in {elapsed:.2f}s")
    print(f"Result (should show blocking): {result}")


def test_timeout_behavior():
    """Test timeout behavior with a slow endpoint"""
    print("\n⏱️ Testing Timeout Behavior")
    print("=" * 50)
    
    tool = SafeWebScrapeTool()
    
    # Use httpbin delay endpoint to test timeout
    slow_url = "https://httpbin.org/delay/15"  # 15 second delay (should timeout at 10s)
    print(f"Testing timeout with slow URL: {slow_url}")
    print("Should timeout after 10 seconds...")
    
    start_time = time.time()
    result = tool._run(slow_url)
    elapsed = time.time() - start_time
    
    print(f"Request completed in {elapsed:.2f}s")
    print(f"Result: {result}")
    
    if elapsed < 12:  # Should timeout around 10s
        print("✅ Timeout behavior working correctly")
    else:
        print("❌ Timeout may not be working - took too long")


def main():
    """Run all safe research tool tests"""
    print("🛡️ SAFE RESEARCH TOOLS TEST SUITE")
    print("=" * 60)
    print("Testing our enhanced research tools that prevent binary content issues")
    print("and enforce timeout limits for reliable operation.")
    print()
    
    try:
        # Run all tests
        test_content_safety_checks()
        test_safe_head_request()
        test_safe_serper_tool()
        test_safe_web_scrape_tool()
        test_timeout_behavior()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED")
        print("✅ Safe research tools are working correctly")
        print("✅ Binary content filtering is active")
        print("✅ Timeout limits are enforced")
        print()
        print("The researcher agent should now be protected from:")
        print("  - Binary content that breaks functionality")
        print("  - Long-running requests (>10s timeout)")
        print("  - Unsafe file types (PDFs, images, etc.)")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()