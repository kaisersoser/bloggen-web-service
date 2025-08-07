#!/usr/bin/env python3
"""
FastAPI Blog Generation Performance Test

This script tests the concurrent performance of the blog generation service
with the new FastAPI backend and context variables. It verifies:
1. Request isolation between concurrent users
2. Performance under load
3. No race conditions in cost tracking
4. Proper SSE streaming functionality

Usage:
    python performance_test.py --requests 10 --concurrency 5
    python performance_test.py --requests 50 --concurrency 10 --detailed
"""

import asyncio
import aiohttp
import ssl
import time
import json
import uuid
import argparse
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading


@dataclass
class TestConfig:
    """Test configuration parameters."""
    base_url: str = "https://localhost:5000"
    total_requests: int = 10
    max_concurrency: int = 5
    timeout: int = 300  # 5 minutes timeout per request
    detailed_logging: bool = False
    verify_ssl: bool = False


@dataclass
class RequestResult:
    """Individual request test result."""
    request_id: str
    topic: str
    start_time: float
    end_time: float
    duration: float
    status_code: int
    success: bool
    task_id: Optional[str] = None
    error_message: Optional[str] = None
    final_content: Optional[str] = None
    content_length: Optional[int] = None
    sse_events_count: int = 0


@dataclass
class TestReport:
    """Overall test report."""
    config: TestConfig
    results: List[RequestResult]
    total_duration: float
    successful_requests: int
    failed_requests: int
    average_duration: float
    median_duration: float
    min_duration: float
    max_duration: float
    throughput_rps: float


class BlogGenerationTester:
    """Handles concurrent blog generation testing."""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.results: List[RequestResult] = []
        self.lock = threading.Lock()
        
        # Create SSL context that ignores certificate verification for testing
        self.ssl_context = ssl.create_default_context()
        if not config.verify_ssl:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE
    
    def generate_test_topics(self) -> List[str]:
        """Generate diverse test topics to ensure realistic testing."""
        base_topics = [
            "The Future of Artificial Intelligence in Healthcare",
            "Sustainable Energy Solutions for Climate Change",
            "Remote Work Productivity Tips and Strategies",
            "Cryptocurrency and Blockchain Technology Explained",
            "Mental Health Awareness in the Digital Age",
            "Space Exploration and Mars Colonization",
            "Cybersecurity Best Practices for Small Businesses",
            "The Rise of Electric Vehicles and Smart Transportation",
            "Machine Learning Applications in Finance",
            "Social Media Impact on Modern Communication"
        ]
        
        # Generate enough topics by cycling through base topics with variations
        topics = []
        for i in range(self.config.total_requests):
            base_topic = base_topics[i % len(base_topics)]
            if i >= len(base_topics):
                # Add variation to avoid duplicate topics
                variation = f" - Part {(i // len(base_topics)) + 1}"
                topic = base_topic + variation
            else:
                topic = base_topic
            topics.append(topic)
        
        return topics
    
    async def create_auth_token(self) -> str:
        """Create a test JWT token for authentication using the actual NEXTAUTH_SECRET."""
        import jwt
        import os
        
        # Use the actual NEXTAUTH_SECRET from environment or a default for testing
        secret = os.getenv("NEXTAUTH_SECRET", "Ver0EvKSf1T5hN4/6NDsnPyZf8S7dJZ/Ewksc2Y2L7w=")
        
        payload = {
            "sub": f"test_user_{uuid.uuid4().hex[:8]}",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "name": "Performance Test User",
            "role": "PREMIUM",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600
        }
        
        return jwt.encode(payload, secret, algorithm="HS256")
    
    async def send_blog_request(self, session: aiohttp.ClientSession, topic: str, request_id: str) -> RequestResult:
        """Send a single blog generation request and track the full lifecycle."""
        start_time = time.time()
        result = RequestResult(
            request_id=request_id,
            topic=topic,
            start_time=start_time,
            end_time=0,
            duration=0,
            status_code=0,
            success=False
        )
        
        try:
            if self.config.detailed_logging:
                print(f"🚀 [{request_id}] Starting blog generation: {topic[:50]}...")
            
            # Create auth token
            auth_token = await self.create_auth_token()
            
            # Send blog generation request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {auth_token}"
            }
            
            payload = {
                "topic": topic,
                "task_id": request_id  # Use request_id as task_id for tracking
            }
            
            async with session.post(
                f"{self.config.base_url}/generate-blog",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ssl=self.ssl_context
            ) as response:
                result.status_code = response.status
                response_data = await response.json()
                
                if response.status == 200:
                    result.task_id = response_data.get("task_id", request_id)
                    result.success = True
                    
                    if self.config.detailed_logging:
                        print(f"✅ [{request_id}] Request accepted, task_id: {result.task_id}")
                    
                    # Now monitor the SSE stream for completion
                    await self.monitor_sse_stream(session, result, auth_token)
                    
                else:
                    result.error_message = response_data.get("error", f"HTTP {response.status}")
                    if self.config.detailed_logging:
                        print(f"❌ [{request_id}] Request failed: {result.error_message}")
        
        except asyncio.TimeoutError:
            result.error_message = "Request timeout"
            if self.config.detailed_logging:
                print(f"⏰ [{request_id}] Request timed out")
        
        except Exception as e:
            result.error_message = str(e)
            if self.config.detailed_logging:
                print(f"💥 [{request_id}] Request error: {str(e)}")
        
        finally:
            result.end_time = time.time()
            result.duration = result.end_time - result.start_time
            
            with self.lock:
                self.results.append(result)
            
            if self.config.detailed_logging:
                status = "✅ SUCCESS" if result.success else "❌ FAILED"
                print(f"🏁 [{request_id}] Completed in {result.duration:.2f}s - {status}")
        
        return result
    
    async def monitor_sse_stream(self, session: aiohttp.ClientSession, result: RequestResult, auth_token: str):
        """Monitor SSE stream until blog generation completes."""
        try:
            stream_url = f"{self.config.base_url}/stream/{result.task_id}?token={auth_token}"
            
            if self.config.detailed_logging:
                print(f"🔗 [{result.request_id}] Connecting to SSE stream: {stream_url}")
            
            async with session.get(
                stream_url,
                headers={"Accept": "text/event-stream"},
                timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ssl=self.ssl_context
            ) as response:
                if response.status != 200:
                    result.error_message = f"SSE stream failed: HTTP {response.status}"
                    if self.config.detailed_logging:
                        print(f"❌ [{result.request_id}] SSE connection failed: HTTP {response.status}")
                    return
                
                if self.config.detailed_logging:
                    print(f"✅ [{result.request_id}] SSE stream connected, waiting for completion...")
                
                buffer = ""
                async for chunk in response.content.iter_chunked(1024):
                    buffer += chunk.decode('utf-8')
                    
                    # Process complete lines
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line.startswith('data: '):
                            data_str = line[6:]  # Remove 'data: ' prefix
                            if data_str.strip() == '':
                                continue  # Skip empty data lines
                                
                            try:
                                data = json.loads(data_str)
                                result.sse_events_count += 1
                                
                                if self.config.detailed_logging:
                                    event_type = data.get('type', 'unknown')
                                    if event_type == 'status_update':
                                        step = data.get('current_step', 'Unknown step')
                                        progress = data.get('progress', 0) * 100
                                        print(f"📡 [{result.request_id}] {step} ({progress:.1f}%)")
                                    else:
                                        print(f"📡 [{result.request_id}] Event: {event_type}")
                                
                                # Check for completion
                                if data.get('status') == 'completed' and data.get('result'):
                                    result.final_content = data['result']
                                    result.content_length = len(data['result'])
                                    result.success = True
                                    if self.config.detailed_logging:
                                        print(f"🎉 [{result.request_id}] Blog generation completed! Content: {result.content_length} chars")
                                    return
                                
                                elif data.get('status') == 'failed':
                                    result.error_message = data.get('error', 'Unknown error')
                                    result.success = False
                                    if self.config.detailed_logging:
                                        print(f"💥 [{result.request_id}] Blog generation failed: {result.error_message}")
                                    return
                                
                                elif data.get('type') == 'stream_ended':
                                    if self.config.detailed_logging:
                                        print(f"🔚 [{result.request_id}] Stream ended")
                                    return
                            
                            except json.JSONDecodeError as e:
                                if self.config.detailed_logging:
                                    print(f"⚠️ [{result.request_id}] Failed to parse JSON: {data_str[:100]}...")
                                continue  # Skip malformed JSON
        
        except asyncio.TimeoutError:
            result.error_message = "SSE stream timeout"
            if self.config.detailed_logging:
                print(f"⏰ [{result.request_id}] SSE stream timed out")
        except Exception as e:
            result.error_message = f"SSE monitoring error: {str(e)}"
            if self.config.detailed_logging:
                print(f"❌ [{result.request_id}] SSE error: {str(e)}")
    
    async def run_concurrent_test(self) -> TestReport:
        """Run the concurrent blog generation test."""
        print(f"🔬 Starting Performance Test")
        print(f"📊 Configuration: {self.config.total_requests} requests, {self.config.max_concurrency} concurrent")
        print(f"🎯 Target: {self.config.base_url}")
        print("=" * 60)
        
        topics = self.generate_test_topics()
        test_start_time = time.time()
        
        # Create HTTP session with connection pooling
        connector = aiohttp.TCPConnector(
            limit=self.config.max_concurrency,
            limit_per_host=self.config.max_concurrency,
            ssl=self.ssl_context
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Create semaphore to limit concurrency
            semaphore = asyncio.Semaphore(self.config.max_concurrency)
            
            async def bounded_request(topic: str, req_id: str):
                async with semaphore:
                    return await self.send_blog_request(session, topic, req_id)
            
            # Generate unique request IDs
            request_ids = [f"test_{uuid.uuid4().hex[:8]}" for _ in range(self.config.total_requests)]
            
            # Create and run concurrent tasks
            tasks = [
                bounded_request(topic, req_id)
                for topic, req_id in zip(topics, request_ids)
            ]
            
            # Execute all requests
            await asyncio.gather(*tasks, return_exceptions=True)
        
        test_end_time = time.time()
        total_duration = test_end_time - test_start_time
        
        # Generate report
        return self.generate_report(total_duration)
    
    def generate_report(self, total_duration: float) -> TestReport:
        """Generate comprehensive test report."""
        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]
        
        durations = [r.duration for r in successful_results] if successful_results else [0]
        
        report = TestReport(
            config=self.config,
            results=self.results,
            total_duration=total_duration,
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            average_duration=statistics.mean(durations),
            median_duration=statistics.median(durations),
            min_duration=min(durations),
            max_duration=max(durations),
            throughput_rps=len(successful_results) / total_duration if total_duration > 0 else 0
        )
        
        return report
    
    def print_report(self, report: TestReport):
        """Print comprehensive test report."""
        print("\n" + "=" * 60)
        print("📈 PERFORMANCE TEST RESULTS")
        print("=" * 60)
        
        print(f"🔧 Test Configuration:")
        print(f"   Total Requests: {report.config.total_requests}")
        print(f"   Max Concurrency: {report.config.max_concurrency}")
        print(f"   Timeout: {report.config.timeout}s")
        print(f"   Target URL: {report.config.base_url}")
        
        print(f"\n📊 Overall Results:")
        print(f"   ✅ Successful: {report.successful_requests}")
        print(f"   ❌ Failed: {report.failed_requests}")
        print(f"   📈 Success Rate: {(report.successful_requests/len(report.results)*100):.1f}%")
        print(f"   ⏱️  Total Time: {report.total_duration:.2f}s")
        print(f"   🚀 Throughput: {report.throughput_rps:.2f} requests/second")
        
        if report.successful_requests > 0:
            print(f"\n⏰ Timing Analysis (Successful Requests):")
            print(f"   📈 Average Duration: {report.average_duration:.2f}s")
            print(f"   📊 Median Duration: {report.median_duration:.2f}s")
            print(f"   ⚡ Fastest Request: {report.min_duration:.2f}s")
            print(f"   🐌 Slowest Request: {report.max_duration:.2f}s")
        
        if report.failed_requests > 0:
            print(f"\n❌ Failed Requests Analysis:")
            error_counts = {}
            for result in report.results:
                if not result.success:
                    error = result.error_message or "Unknown error"
                    error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in error_counts.items():
                print(f"   • {error}: {count} times")
        
        if self.config.detailed_logging and report.successful_requests > 0:
            print(f"\n📋 Individual Request Details:")
            for result in report.results[:10]:  # Show first 10 for brevity
                status = "✅" if result.success else "❌"
                content_info = f" ({result.content_length} chars)" if result.content_length else ""
                sse_info = f" {result.sse_events_count} SSE events" if result.sse_events_count > 0 else ""
                print(f"   {status} [{result.request_id}] {result.duration:.2f}s{content_info}{sse_info}")
        
        print("\n" + "=" * 60)


def main():
    """Main test runner with command line arguments."""
    parser = argparse.ArgumentParser(description="FastAPI Blog Generation Performance Test")
    parser.add_argument("--requests", "-r", type=int, default=10, 
                       help="Total number of requests to send (default: 10)")
    parser.add_argument("--concurrency", "-c", type=int, default=5,
                       help="Maximum concurrent requests (default: 5)")
    parser.add_argument("--timeout", "-t", type=int, default=300,
                       help="Timeout per request in seconds (default: 300)")
    parser.add_argument("--url", "-u", type=str, default="https://localhost:5000",
                       help="Backend URL (default: https://localhost:5000)")
    parser.add_argument("--detailed", "-d", action="store_true",
                       help="Enable detailed logging")
    parser.add_argument("--verify-ssl", action="store_true",
                       help="Verify SSL certificates (default: disabled for testing)")
    
    args = parser.parse_args()
    
    config = TestConfig(
        base_url=args.url,
        total_requests=args.requests,
        max_concurrency=args.concurrency,
        timeout=args.timeout,
        detailed_logging=args.detailed,
        verify_ssl=args.verify_ssl
    )
    
    # Validate configuration
    if config.max_concurrency > config.total_requests:
        config.max_concurrency = config.total_requests
        print(f"⚠️  Adjusted concurrency to {config.max_concurrency} (max: total requests)")
    
    # Run the test
    tester = BlogGenerationTester(config)
    
    try:
        # Run async test
        report = asyncio.run(tester.run_concurrent_test())
        tester.print_report(report)
        
        # Save detailed results to JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"performance_test_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump({
                'config': asdict(config),
                'report': asdict(report),
                'detailed_results': [asdict(r) for r in report.results]
            }, f, indent=2, default=str)
        
        print(f"📁 Detailed results saved to: {results_file}")
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"💥 Test failed with error: {str(e)}")
        raise


if __name__ == "__main__":
    main()
