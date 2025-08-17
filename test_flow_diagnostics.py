#!/usr/bin/env python3
"""
Comprehensive diagnostic script to test BlogGenerationFlow and identify failure points.
"""
import sys
import os
import asyncio
import traceback
from datetime import datetime

# Load environment variables first
from dotenv import load_dotenv
load_dotenv('/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/.env')

# Add backend src to path
sys.path.append('/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src')

async def test_blog_generation_flow():
    print("🔍 COMPREHENSIVE BLOG GENERATION DIAGNOSTICS")
    print("=" * 60)
    
    try:
        # Test 1: Environment Variables
        print("\n1. Testing Environment Variables...")
        
        required_vars = ['OPENAI_API_KEY', 'SERPER_API_KEY', 'UNSPLASH_ACCESS_KEY']
        for var in required_vars:
            value = os.getenv(var)
            if value:
                print(f"   ✅ {var}: {value[:10]}...{value[-4:] if len(value) > 14 else ''}")
            else:
                print(f"   ❌ {var}: Missing!")
        
        # Fix user issue by using an existing user ID from database
        print("\n2. Testing Database Connection...")
        from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker
        
        # Use a valid user ID that exists in the database
        audit_tracker = EnhancedDatabaseAuditTracker(
            session_type="diagnostic_test",
            user_id="cmebutx3a00000z983mtma7n8j",  # Use existing user ID
            blog_id="test_blog_123"
        )
        
        await audit_tracker.start_session()
        print("   ✅ Database connection and audit tracker working")
        
        # Test 3: Context Variables
        print("\n3. Testing Context Variables...")
        from core.context_vars import (
            set_request_context,
            set_audit_context,
            current_request_id,
            current_user_id
        )
        
        # Set request context
        set_request_context(
            request_id="diag_123",
            task_id="diag_task_123",
            user_id="diag_user",
            user_email="test@diagnostic.com",
            user_role="PREMIUM",
            blog_id="diag_blog_123",
            topic="Diagnostic Test Topic"
        )
        
        set_audit_context(audit_tracker, "diag_session_123")
        
        print(f"   ✅ Request ID: {current_request_id.get()}")
        print(f"   ✅ User ID: {current_user_id.get()}")
        
        # Test 4: Basic Imports
        print("\n4. Testing Core Imports...")
        try:
            from bloggen.flows import BlogGenerationFlow
            print("   ✅ BlogGenerationFlow imported successfully")
        except Exception as e:
            print(f"   ❌ BlogGenerationFlow import failed: {e}")
            return
        
        try:
            from crewai import Agent, Task, Crew
            print("   ✅ CrewAI components imported successfully")
        except Exception as e:
            print(f"   ❌ CrewAI import failed: {e}")
            return
        
        # Test 5: Flow Initialization
        print("\n5. Testing Flow Initialization...")
        
        def status_callback(status_data):
            print(f"   📊 Status Update: {status_data}")
        
        try:
            flow = BlogGenerationFlow(
                status_callback=status_callback,
                user_id="diag_user",
                blog_id="diag_blog_123",
                audit_tracker=audit_tracker,
                topic="The Future of Artificial Intelligence",
                instructions="Write a comprehensive blog post about AI trends"
            )
            print("   ✅ BlogGenerationFlow initialized successfully")
        except Exception as e:
            print(f"   ❌ Flow initialization failed: {e}")
            traceback.print_exc()
            return
        
        # Test 6: Tool Testing
        print("\n6. Testing Individual Tools...")
        
        # Test OpenAI Tool
        try:
            from bloggen.tools.openai_image_tool import OpenAIImageTool
            openai_tool = OpenAIImageTool(audit_tracker=audit_tracker)
            print("   ✅ OpenAI Image Tool initialized")
        except Exception as e:
            print(f"   ⚠️ OpenAI Image Tool failed: {e}")
        
        # Test Unsplash Tool
        try:
            from bloggen.tools.unsplash_tool import UnsplashImageTool
            unsplash_tool = UnsplashImageTool()
            print("   ✅ Unsplash Tool initialized")
        except Exception as e:
            print(f"   ⚠️ Unsplash Tool failed: {e}")
        
        # Test Serper Tool
        try:
            from crewai_tools import SerperDevTool
            serper_tool = SerperDevTool()
            print("   ✅ Serper Search Tool initialized")
        except Exception as e:
            print(f"   ⚠️ Serper Tool failed: {e}")
        
        # Test 7: Simple Flow Execution (Research Phase Only)
        print("\n7. Testing Flow Research Phase...")
        
        try:
            # Test just the research phase to isolate issues
            print("   🔬 Creating research agent...")
            
            # Get research tools from the flow's tools manager
            research_tools = flow.tools_manager.get_research_tools()
            print(f"   ✅ Research tools loaded: {len(research_tools)} tools")
            
            # Create a simple research agent
            research_agent = Agent(
                role='Research Specialist',
                goal='Research the given topic thoroughly',
                backstory='You are an expert researcher',
                tools=research_tools,
                verbose=True,
                allow_delegation=False
            )
            print("   ✅ Research agent created successfully")
            
            # Create a simple task
            research_task = Task(
                description='Research the topic: The Future of Artificial Intelligence. Find 3 key trends.',
                expected_output='A list of 3 key AI trends with brief descriptions',
                agent=research_agent
            )
            print("   ✅ Research task created successfully")
            
            # Create and run a minimal crew
            research_crew = Crew(
                agents=[research_agent],
                tasks=[research_task],
                verbose=True
            )
            print("   ✅ Research crew created successfully")
            
            print("   🚀 Starting research execution (this may take a moment)...")
            research_result = research_crew.kickoff()
            print(f"   ✅ Research completed! Result length: {len(str(research_result))} characters")
            print(f"   📄 Research preview: {str(research_result)[:200]}...")
            
        except Exception as e:
            print(f"   ❌ Research phase failed: {e}")
            print("\n🔍 DETAILED ERROR TRACEBACK:")
            traceback.print_exc()
            
            # Try to identify specific error types
            if "API" in str(e).upper():
                print("\n💡 DIAGNOSIS: API-related error detected")
                print("   - Check API keys and rate limits")
                print("   - Verify internet connectivity")
            elif "IMPORT" in str(e).upper():
                print("\n💡 DIAGNOSIS: Import-related error detected")
                print("   - Check if all dependencies are installed")
                print("   - Verify Python path and module locations")
            elif "CONTEXT" in str(e).upper():
                print("\n💡 DIAGNOSIS: Context-related error detected")
                print("   - Check context variable setup")
                print("   - Verify audit tracker configuration")
            
            return
        
        # Test 8: Full Flow Execution (if research worked)
        print("\n8. Testing Full Flow Execution...")
        
        try:
            print("   🚀 Starting full blog generation flow...")
            
            # Set the flow properties
            flow.topic = "The Future of Artificial Intelligence"
            flow.current_year = datetime.now().year
            
            # Execute the full flow
            result = flow.kickoff({
                'topic': flow.topic,
                'current_year': flow.current_year,
            })
            
            print(f"   ✅ FULL FLOW COMPLETED! Result type: {type(result)}")
            
            # Extract content
            if hasattr(result, 'raw'):
                content = result.raw
            elif isinstance(result, dict) and 'final_blog_post' in result:
                content = str(result['final_blog_post'])
            else:
                content = str(result)
            
            print(f"   📊 Generated content length: {len(content)} characters")
            print(f"   📄 Content preview: {content[:300]}...")
            
            print("\n🎉 DIAGNOSIS COMPLETE: Blog generation is working!")
            
        except Exception as e:
            print(f"   ❌ Full flow failed: {e}")
            print("\n🔍 DETAILED ERROR TRACEBACK:")
            traceback.print_exc()
            
            print("\n💡 ANALYSIS:")
            print("   - Research phase worked, but full flow failed")
            print("   - Issue is likely in content generation or fact-checking phases")
            print("   - Check agent configurations and task definitions")
        
        # Clean up
        await audit_tracker.end_session()
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        traceback.print_exc()

def run_sync_wrapper():
    """Wrapper to run async function in sync context"""
    return asyncio.run(test_blog_generation_flow())

if __name__ == "__main__":
    print("🚀 Starting Blog Generation Diagnostics...")
    run_sync_wrapper()
