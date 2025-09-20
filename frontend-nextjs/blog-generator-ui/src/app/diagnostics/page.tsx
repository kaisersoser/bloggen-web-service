"use client"

import { useSession } from 'next-auth/react';
import { SSEConnectionTester } from '@/components/diagnostics/SSEConnectionTester';
import { RedisSSEComparisonTester } from '@/components/diagnostics/RedisSSEComparisonTester';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

export default function DiagnosticsPage() {
  const { data: session, status } = useSession();

  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading authentication...</p>
        </div>
      </div>
    );
  }

  if (status !== 'authenticated') {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="p-6">
            <div className="text-center">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                Authentication Required
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Please sign in to access the diagnostic tools.
              </p>
              <a
                href="/api/auth/signin"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Sign In
              </a>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              🔧 System Diagnostics
            </h1>
            <a
              href="/blog"
              className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors flex items-center gap-1"
            >
              ← Back to Blog Generator
            </a>
          </div>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Diagnostic tools for testing SSE connections, Redis monitoring, and notification flow analysis.
          </p>
          <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900 border border-blue-200 rounded-md">
            <p className="text-blue-800 dark:text-blue-200 text-sm">
              <strong>Signed in as:</strong> {session.user?.email} ({session.user?.role || 'USER'})
            </p>
          </div>
        </div>

        <div className="space-y-8">
          {/* SSE Message Reception Analysis */}
          <section>
            <div className="mb-4">
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
                � SSE Message Reception Analysis
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Monitor SSE message reception and analyze against expected message types. 
                Use the comprehensive backend Python scripts to compare what's published to Redis vs what reaches the frontend.
              </p>
            </div>
            <RedisSSEComparisonTester />
          </section>

          {/* SSE Connection Testing */}
          <section>
            <div className="mb-4">
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
                � SSE Connection Testing
              </h2>
              <p className="text-gray-600 dark:text-gray-400">
                Test SSE connections independently of the main UI to verify authentication, message reception, and statistics.
              </p>
            </div>
            <SSEConnectionTester />
          </section>

          {/* Diagnostic Instructions */}
          <section>
            <Card>
              <CardHeader>
                <CardTitle>📋 Diagnostic Instructions</CardTitle>
                <CardDescription>
                  How to use these tools effectively for troubleshooting
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                      1. SSE Message Reception Analysis
                    </h3>
                    <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1 ml-4">
                      <li>• Enter a task ID and click "Start Monitoring"</li>
                      <li>• Generate a blog on the main page using the same task ID</li>
                      <li>• Monitor SSE message reception and coverage analysis</li>
                      <li>• Use "Copy Report" to save detailed analysis</li>
                      <li>• Run backend Python scripts to compare Redis publication vs SSE reception</li>
                    </ul>
                  </div>
                  
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                      2. Backend Analysis Scripts
                    </h3>
                    <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1 ml-4">
                      <li>• <code>python comprehensive_notification_analysis.py</code> - Analyze what backend publishes to Redis</li>
                      <li>• <code>python redis_sse_diagnostic.py &lt;task_id&gt;</code> - Monitor Redis channels during live generation</li>
                      <li>• Compare Redis publication count vs frontend SSE reception count</li>
                      <li>• Identify which message types are lost between Redis and SSE delivery</li>
                    </ul>
                  </div>
                  
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                      3. SSE Connection Testing
                    </h3>
                    <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1 ml-4">
                      <li>• Connect to an existing task ID or create a new blog generation</li>
                      <li>• Monitor message reception and categorization</li>
                      <li>• Check authentication flow and connection stability</li>
                      <li>• Review message statistics and types received</li>
                    </ul>
                  </div>
                  
                  <div>
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
                      4. Troubleshooting Tips
                    </h3>
                    <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1 ml-4">
                      <li>• Ensure backend server is running on port 5000</li>
                      <li>• Check that Redis server is running and accessible</li>
                      <li>• Use browser dev tools to inspect network connections</li>
                      <li>• Compare message counts between tools to identify bottlenecks</li>
                      <li>• Look for specific message types missing from SSE stream</li>
                      <li>• Use comprehensive backend analysis to verify Redis publication</li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          </section>
        </div>
      </div>
    </div>
  );
}