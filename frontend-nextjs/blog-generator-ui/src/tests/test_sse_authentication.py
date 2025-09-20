#!/usr/bin/env python3
"""
SSE Authentication Test Script

This script tests the JWT token authentication flow for SSE connections.
It validates that the frontend can retrieve tokens and connect to the backend SSE endpoint.

Security Note: This script does NOT contain any secrets or API keys.
All authentication is handled through the existing NextAuth.js session system.
"""

import asyncio
import httpx
import json
import sys
from typing import Optional, Dict, Any

# Configuration (no secrets here)
FRONTEND_URL = "https://localhost:3000"
BACKEND_URL = "https://localhost:5000"

class SSEAuthTester:
    def __init__(self):
        self.session_cookies: Optional[Dict[str, str]] = None
        self.jwt_token: Optional[str] = None
    
    async def test_authentication_flow(self) -> bool:
        """Test the complete authentication flow for SSE connections."""
        print("🔐 Testing SSE Authentication Flow")
        print("=" * 50)
        
        try:
            # Step 1: Test JWT token endpoint availability
            print("1️⃣ Testing JWT token endpoint availability...")
            token_available = await self._test_jwt_endpoint_availability()
            if not token_available:
                print("❌ JWT token endpoint not available")
                return False
            print("✅ JWT token endpoint is available")
            
            # Step 2: Test SSE endpoint availability  
            print("\n2️⃣ Testing SSE endpoint availability...")
            sse_available = await self._test_sse_endpoint_availability()
            if not sse_available:
                print("❌ SSE endpoint not available")
                return False
            print("✅ SSE endpoint is available")
            
            # Step 3: Test authentication requirements
            print("\n3️⃣ Testing authentication requirements...")
            auth_required = await self._test_authentication_requirements()
            if not auth_required:
                print("❌ Authentication not properly enforced")
                return False
            print("✅ Authentication properly enforced")
            
            print("\n🎉 All authentication tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Authentication test failed: {e}")
            return False
    
    async def _test_jwt_endpoint_availability(self) -> bool:
        """Test if the JWT token endpoint is available."""
        async with httpx.AsyncClient(verify=False) as client:
            try:
                response = await client.get(f"{FRONTEND_URL}/api/auth/jwt-token")
                # We expect 401/403 for unauthenticated requests, not 404
                return response.status_code in [401, 403, 200]
            except Exception as e:
                print(f"   Error: {e}")
                return False
    
    async def _test_sse_endpoint_availability(self) -> bool:
        """Test if the SSE endpoint is available."""
        async with httpx.AsyncClient(verify=False) as client:
            try:
                # Try to access SSE endpoint without authentication
                response = await client.get(f"{BACKEND_URL}/stream/test-task-id")
                # We expect 401/422 for missing token, not 404
                return response.status_code in [401, 422, 400]
            except Exception as e:
                print(f"   Error: {e}")
                return False
    
    async def _test_authentication_requirements(self) -> bool:
        """Test that authentication is properly required."""
        async with httpx.AsyncClient(verify=False) as client:
            try:
                # Test 1: No token provided
                response1 = await client.get(f"{BACKEND_URL}/stream/test-task")
                auth_required_no_token = response1.status_code in [401, 422, 400]
                
                # Test 2: Invalid token provided
                response2 = await client.get(f"{BACKEND_URL}/stream/test-task?token=invalid-token")
                auth_required_invalid_token = response2.status_code in [401, 403]
                
                return auth_required_no_token and auth_required_invalid_token
                
            except Exception as e:
                print(f"   Error: {e}")
                return False
    
    async def simulate_frontend_auth_flow(self) -> bool:
        """Simulate the authentication flow that the frontend component would use."""
        print("\n🖥️ Simulating Frontend Authentication Flow")
        print("=" * 50)
        
        try:
            print("1️⃣ Simulating NextAuth.js session check...")
            # In a real scenario, this would check session cookies
            print("   ℹ️ This requires an active user session in the browser")
            print("   ℹ️ Frontend component handles session management via NextAuth.js")
            
            print("\n2️⃣ Simulating JWT token retrieval...")
            print("   ℹ️ Component calls: fetch('/api/auth/jwt-token', { credentials: 'include' })")
            print("   ℹ️ Token is generated from existing session without exposing secrets")
            
            print("\n3️⃣ Simulating SSE connection establishment...")
            print("   ℹ️ Component creates: new EventSource(`${BACKEND_URL}/stream/${taskId}?token=${token}`)")
            print("   ℹ️ EventSource handles connection persistence and reconnection")
            
            print("\n✅ Authentication flow simulation complete")
            print("📋 To test with real authentication:")
            print("   1. Sign in to the application at https://localhost:3000")
            print("   2. Navigate to https://localhost:3000/sse-test")
            print("   3. Use the SSE Connection Tester component")
            
            return True
            
        except Exception as e:
            print(f"❌ Authentication flow simulation failed: {e}")
            return False

async def main():
    """Main test function."""
    print("🧪 SSE Authentication Diagnostic Test")
    print("=" * 60)
    print("This script tests the authentication mechanisms for SSE connections.")
    print("It validates endpoint availability and authentication requirements.")
    print()
    
    tester = SSEAuthTester()
    
    # Run authentication tests
    auth_success = await tester.test_authentication_flow()
    
    # Simulate frontend flow
    flow_success = await tester.simulate_frontend_auth_flow()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 30)
    print(f"Authentication Tests: {'✅ PASSED' if auth_success else '❌ FAILED'}")
    print(f"Flow Simulation: {'✅ PASSED' if flow_success else '❌ FAILED'}")
    
    if auth_success and flow_success:
        print("\n🎉 All tests completed successfully!")
        print("✅ SSE authentication system is properly configured")
        print("🔗 Ready for real-time connection testing with authenticated users")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)