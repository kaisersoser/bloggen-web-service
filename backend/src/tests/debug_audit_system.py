#!/usr/bin/env python3
"""
Audit System Debug and Validation Script

This script helps diagnose why audit data is showing zeros in the database
instead of real API costs. It tests the complete audit pipeline:

1. Context variable functionality
2. LLM interceptor callback registration
3. Direct OpenAI API calls vs CrewAI calls
4. Database persistence
"""

import asyncio
import os
import sys
import json
from datetime import datetime

# Add the backend src to path
sys.path.insert(0, '/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src')

from core.context_vars import (
    set_request_context,
    set_audit_context,
    current_audit_tracker,
    current_phase,
    get_context_summary
)
from core.audit_tracker import DatabaseAuditTracker
from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker
from core.llm_interceptor import setup_llm_interceptor

# Test direct OpenAI calls
import openai

# Test LiteLLM calls
try:
    import litellm
    LITELLM_AVAILABLE = True
    print("✅ LiteLLM is available")
except ImportError:
    LITELLM_AVAILABLE = False
    print("❌ LiteLLM is NOT available")

# Test CrewAI imports
try:
    from crewai import Agent, Task, Crew
    CREWAI_AVAILABLE = True
    print("✅ CrewAI is available")
except ImportError:
    CREWAI_AVAILABLE = False
    print("❌ CrewAI is NOT available")


async def test_audit_system():
    """Run comprehensive audit system tests."""
    
    print("\n" + "="*70)
    print("🔍 AUDIT SYSTEM DIAGNOSTIC TEST")
    print("="*70)
    
    # Test 1: Context Variables
    print("\n1️⃣ Testing Context Variables...")
    try:
        # Set up request context
        set_request_context(
            request_id="test_123",
            task_id="debug_task_456",
            user_id="debug_user",
            user_email="debug@test.com",
            user_role="PREMIUM",
            blog_id="debug_blog_789",
            topic="AI Testing"
        )
        
        # Create audit tracker - USING ENHANCED VERSION (valid user_id from database)
        audit_tracker = EnhancedDatabaseAuditTracker(
            session_type="debug_test",
            user_id="cmdaiv5530000z9nxqmyg445v",  # Valid user ID from database
            blog_id=None  # Use None instead of fake ID to avoid foreign key constraint
        )
        
        # Set audit context
        set_audit_context(audit_tracker, "debug_session_001")
        
        # Test context retrieval
        context_tracker = current_audit_tracker.get(None)
        if context_tracker:
            print("✅ Context variables working - audit tracker found")
            if hasattr(context_tracker, 'session_type'):
                print(f"   Session type: {context_tracker.session_type}")  # type: ignore
                print(f"   User ID: {context_tracker.user_id}")  # type: ignore
                print(f"   Blog ID: {context_tracker.blog_id}")  # type: ignore
            else:
                print("   Tracker found but attributes not accessible")
        else:
            print("❌ Context variables NOT working - no audit tracker found")
            return False
            
    except Exception as e:
        print(f"❌ Context variables test failed: {e}")
        return False
    
    # Test 2: LLM Interceptor Setup
    print("\n2️⃣ Testing LLM Interceptor Setup...")
    try:
        callback_handler = setup_llm_interceptor()
        if callback_handler:
            print("✅ LLM interceptor setup successful")
            if LITELLM_AVAILABLE:
                print(f"   Success callbacks: {len(litellm.success_callback) if hasattr(litellm, 'success_callback') else 0}")
                print(f"   Failure callbacks: {len(litellm.failure_callback) if hasattr(litellm, 'failure_callback') else 0}")
            else:
                print("   ⚠️ LiteLLM not available - interceptor disabled")
        else:
            print("❌ LLM interceptor setup failed")
            
    except Exception as e:
        print(f"❌ LLM interceptor test failed: {e}")
    
    # Test 3: Database Connection
    print("\n3️⃣ Testing Database Connection...")
    try:
        await audit_tracker.start_session()
        print("✅ Database session started successfully")
        
        # Test manual API call tracking
        print("   Testing manual API call tracking...")
        await audit_tracker.track_api_call(
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
            phase="debug_test",
            agent_role="test_agent"
        )
        print("✅ Manual API call tracked successfully")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    # Test 4: Direct OpenAI API Call
    print("\n4️⃣ Testing Direct OpenAI API Call...")
    try:
        if os.getenv('OPENAI_API_KEY'):
            print("   Making direct OpenAI API call...")
            
            # Set phase for interceptor
            current_phase.set("openai_direct_test")
            
            # Make a simple OpenAI call
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say 'Hello audit test'"}],
                max_tokens=10
            )
            
            print(f"✅ OpenAI API call successful: {response.choices[0].message.content}")
            print(f"   Usage: {response.usage}")
            
        else:
            print("⚠️ No OPENAI_API_KEY found - skipping direct OpenAI test")
            
    except Exception as e:
        print(f"❌ Direct OpenAI test failed: {e}")
    
    # Test 5: LiteLLM API Call (if available)
    print("\n5️⃣ Testing LiteLLM API Call...")
    try:
        if LITELLM_AVAILABLE and os.getenv('OPENAI_API_KEY'):
            print("   Making LiteLLM API call...")
            
            # Set phase for interceptor
            current_phase.set("litellm_test")
            
            # Make a LiteLLM call
            response = litellm.completion(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say 'Hello LiteLLM audit test'"}],
                max_tokens=10
            )
            
            print(f"✅ LiteLLM API call successful: {response.choices[0].message.content}")  # type: ignore
            if hasattr(response, 'usage') and response.usage:  # type: ignore
                print(f"   Usage: {response.usage}")  # type: ignore
            else:
                print("   Usage data not available")
            
        else:
            print("⚠️ LiteLLM not available or no API key - skipping LiteLLM test")
            
    except Exception as e:
        print(f"❌ LiteLLM test failed: {e}")
    
    # Test 6: CrewAI Agent Call (if available)
    print("\n6️⃣ Testing CrewAI Agent Call...")
    try:
        if CREWAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
            print("   Creating simple CrewAI agent...")
            
            # Set phase for interceptor
            current_phase.set("crewai_test")
            
            # Create a simple agent
            test_agent = Agent(
                role='Test Agent',
                goal='Say hello for audit testing',
                backstory='A simple agent for testing audit tracking',
                verbose=True,
                allow_delegation=False
            )
            
            # Create a simple task
            test_task = Task(
                description='Say "Hello from CrewAI audit test" in exactly 5 words.',
                agent=test_agent,
                expected_output='A 5-word greeting message.'
            )
            
            # Execute the task
            crew = Crew(
                agents=[test_agent],
                tasks=[test_task],
                verbose=True
            )
            
            print("   Executing CrewAI task...")
            result = crew.kickoff()
            print(f"✅ CrewAI execution successful: {result}")
            
        else:
            print("⚠️ CrewAI not available or no API key - skipping CrewAI test")
            
    except Exception as e:
        print(f"❌ CrewAI test failed: {e}")
    
    # Test 7: Check Audit Data
    print("\n7️⃣ Checking Audit Data in Database...")
    try:
        # End the session to flush data
        await audit_tracker.end_session()
        print("✅ Audit session ended successfully")
        
        # Note: We can't easily query the database from here without 
        # implementing the full database query logic, but we can check logs
        print("   Check the database manually for entries with session 'debug_test'")
        
    except Exception as e:
        print(f"❌ Audit data check failed: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("🏁 DIAGNOSTIC SUMMARY")
    print("="*70)
    print("To fix audit issues, check:")
    print("1. Are LiteLLM callbacks properly registered?")
    print("2. Is CrewAI using LiteLLM for OpenAI calls?")
    print("3. Are context variables preserved in background tasks?")
    print("4. Is the audit tracker receiving callback data?")
    print("5. Are database transactions completing successfully?")
    
    return True


async def main():
    """Main diagnostic function."""
    print("Starting audit system diagnostic...")
    await test_audit_system()
    print("\nDiagnostic complete!")


if __name__ == "__main__":
    asyncio.run(main())
