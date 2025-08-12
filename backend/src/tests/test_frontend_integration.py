#!/usr/bin/env python3
"""
Comprehensive Frontend Integration Test

This test simulates actual frontend API calls to debug why images are not being generated properly.
It tests both the legacy API and the main FastAPI endpoints.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import requests
import json
import time
import subprocess
import signal
from concurrent.futures import ThreadPoolExecutor
from bloggen.content_validator import ContentValidator

def test_legacy_api_call():
    """Test the legacy Flask API endpoint that might be used by frontend."""
    print("🧪 Testing Legacy Flask API (/api/generate-blog)")
    
    # Test data simulating frontend request
    test_data = {
        "topic": "AI Image Generation Tools in 2025",
        "current_year": 2025
    }
    
    try:
        response = requests.post(
            "http://localhost:5000/api/generate-blog",
            json=test_data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('content', '')
            
            print("✅ Legacy API Response received")
            print(f"📊 Content length: {len(content)}")
            
            # Validate content for image issues
            validation = ContentValidator.validate_content(content)
            ContentValidator.log_validation_results(validation, "Legacy API")
            
            # Print first few lines for debugging
            print("\n📝 Content Preview:")
            print(content[:500] + "..." if len(content) > 500 else content)
            
            return validation
        else:
            print(f"❌ Legacy API failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("⚠️ Legacy API server not running on localhost:5000")
        return None
    except Exception as e:
        print(f"❌ Legacy API test failed: {e}")
        return None

def test_main_api_call():
    """Test the main FastAPI endpoint."""
    print("\n🧪 Testing Main FastAPI (/generate-blog)")
    
    # Test data simulating frontend request
    test_data = {
        "topic": "AI Image Generation Tools in 2025",
        "instructions": "Create a comprehensive blog about AI image generation tools with proper images"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/generate-blog",
            json=test_data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            
            print(f"✅ Main API Task created: {task_id}")
            
            # Poll for completion (simulate frontend behavior)
            for attempt in range(60):  # 5 minutes max
                try:
                    status_response = requests.get(f"http://localhost:8000/task-status/{task_id}")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get('status')
                        
                        print(f"📊 Status: {status}")
                        
                        if status == 'completed':
                            content = status_data.get('content', '')
                            
                            # Validate content
                            validation = ContentValidator.validate_content(content)
                            ContentValidator.log_validation_results(validation, "Main API")
                            
                            print("\n📝 Content Preview:")
                            print(content[:500] + "..." if len(content) > 500 else content)
                            
                            return validation
                        elif status == 'failed':
                            print(f"❌ Task failed: {status_data.get('error')}")
                            return None
                    
                    time.sleep(5)
                except Exception as e:
                    print(f"⚠️ Status check failed: {e}")
                    time.sleep(5)
            
            print("⏰ Task timed out")
            return None
            
        else:
            print(f"❌ Main API failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("⚠️ Main API server not running on localhost:8000")
        return None
    except Exception as e:
        print(f"❌ Main API test failed: {e}")
        return None

def test_direct_flow_call():
    """Test the BlogGenerationFlow directly as configured in main.py."""
    print("\n🧪 Testing Direct BlogGenerationFlow (as in main.py)")
    
    try:
        from bloggen.flows import BlogGenerationFlow
        from core.audit_tracker import DatabaseAuditTracker
        
        # Create audit tracker like main.py does
        audit_tracker = DatabaseAuditTracker(
            session_type="blog_generation",
            user_id="test_frontend_user",
            blog_id="test_frontend_blog"
        )
        
        def status_callback(message, status_type="progress", **kwargs):
            print(f"📊 Flow Status: {message} ({status_type})")
            
        # Configure flow exactly like main.py
        flow = BlogGenerationFlow(
            status_callback=status_callback,
            user_id="test_frontend_user",
            blog_id="test_frontend_blog",
            audit_tracker=audit_tracker,
            topic="AI Image Generation Tools in 2025",
            current_year=2025,
            instructions="Create a comprehensive blog about AI image generation tools with proper images"
        )
        
        print("🚀 Starting BlogGenerationFlow...")
        result = flow.kickoff()
        
        content = str(result) if result else ""
        
        # Validate content
        validation = ContentValidator.validate_content(content)
        ContentValidator.log_validation_results(validation, "Direct Flow")
        
        print("\n📝 Content Preview:")
        print(content[:500] + "..." if len(content) > 500 else content)
        
        return validation
        
    except Exception as e:
        print(f"❌ Direct flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def run_frontend_simulation_tests():
    """Run comprehensive frontend simulation tests."""
    print("🚀 Starting Frontend Integration Test Suite")
    print("="*60)
    
    results = {}
    
    # Test 1: Direct Flow (should work with our enhancements)
    results['direct_flow'] = test_direct_flow_call()
    
    # Test 2: Legacy API (may have issues)  
    results['legacy_api'] = test_legacy_api_call()
    
    # Test 3: Main API (should work if server is running)
    results['main_api'] = test_main_api_call()
    
    # Analyze results
    print("\n" + "="*60)
    print("🎯 FRONTEND INTEGRATION TEST RESULTS")
    print("="*60)
    
    for test_name, validation in results.items():
        if validation:
            status = "✅ PASS" if validation['valid'] else "❌ FAIL"
            print(f"{test_name.upper()}: {status}")
            print(f"  - Total Images: {validation['total_images']}")
            print(f"  - Valid Images: {validation['valid_images']}")
            print(f"  - Deprecated Images: {validation['deprecated_images']}")
        else:
            print(f"{test_name.upper()}: ⚠️ NO RESULT")
    
    # Summary
    failed_tests = [name for name, val in results.items() if val and not val['valid']]
    if failed_tests:
        print(f"\n❌ FAILED TESTS: {', '.join(failed_tests)}")
        print("🔧 These components need debugging!")
    else:
        print(f"\n✅ All available tests passed!")

if __name__ == "__main__":
    run_frontend_simulation_tests()
