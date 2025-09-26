"use client"

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useSession } from 'next-auth/react';
import { API_BASE_URL } from '@/config/constants';
import { logger } from '@/lib/logger';

interface SSEMessage {
  id: number;
  timestamp: string;
  type: string;
  data: any;
  rawMessage: string;
  latency?: number;
}

interface MessageStats {
  sseMessages: number;
  sseTypes: Record<string, number>;
  expectedTypes: string[];
  missingTypes: string[];
}

export function RedisSSEComparisonTester() {
  const { status } = useSession();
  const [taskId, setTaskId] = useState<string>('');
  const [isMonitoring, setIsMonitoring] = useState<boolean>(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [sseMessages, setSSEMessages] = useState<SSEMessage[]>([]);
  const [activeTab, setActiveTab] = useState<'comparison' | 'sse' | 'analysis'>('comparison');
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const messageCounterRef = useRef<number>(0);

  // Get JWT token
  const getAuthToken = useCallback(async (): Promise<string> => {
    try {
      const tokenResponse = await fetch('/api/auth/jwt-token', {
        method: 'GET',
        credentials: 'include'
      });
      
      if (!tokenResponse.ok) {
        throw new Error(`Failed to get auth token: ${tokenResponse.status}`);
      }
      
      const { token } = await tokenResponse.json();
      if (!token) {
        throw new Error('No authentication token received');
      }
      
      return token;
    } catch (error) {
      logger.error('❌ Failed to get auth token', error);
      throw error;
    }
  }, []);

  // Start SSE monitoring
  const startSSEMonitoring = useCallback(async (token: string) => {
    try {
  const streamUrl = `${API_BASE_URL}/stream/${taskId.trim()}?token=${encodeURIComponent(token)}`;
  logger.info('🔗 Starting SSE monitoring', { streamUrl });
      
      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        logger.info('✅ SSE connection established');
      };

      eventSource.onmessage = (event) => {
        const receivedTime = Date.now();
        messageCounterRef.current++;
        
        try {
          const data = JSON.parse(event.data);
          const messageType = data.message_type || data.type || 'unknown';
          
          let latency: number | undefined;
          if (data.timestamp) {
            const sentTime = new Date(data.timestamp).getTime();
            latency = receivedTime - sentTime;
          }
          
          const sseMessage: SSEMessage = {
            id: messageCounterRef.current,
            timestamp: new Date(receivedTime).toISOString(),
            type: messageType,
            data: data,
            rawMessage: event.data,
            latency: latency
          };
          
          setSSEMessages(prev => [sseMessage, ...prev.slice(0, 99)]);
          logger.info('🔵 SSE message received', { messageType, data });
          
        } catch (parseError) {
          logger.error('❌ Failed to parse SSE message', parseError);
        }
      };

      eventSource.onerror = (error) => {
        logger.error('❌ SSE connection error', error);
        setConnectionError('SSE connection failed');
      };

    } catch (error) {
      logger.error('❌ Failed to start SSE monitoring', error);
      setConnectionError(error instanceof Error ? error.message : 'Unknown SSE error');
    }
  }, [taskId]);

  // Start monitoring
  const startMonitoring = useCallback(async () => {
    if (!taskId.trim()) {
      setConnectionError('Please enter a task ID');
      return;
    }

    try {
      setConnectionError(null);
      setSSEMessages([]);
      messageCounterRef.current = 0;
      
      const token = await getAuthToken();
      await startSSEMonitoring(token);
      setIsMonitoring(true);
      
    } catch (error) {
      logger.error('❌ Failed to start monitoring', error);
      setConnectionError(error instanceof Error ? error.message : 'Unknown connection error');
    }
  }, [taskId, getAuthToken, startSSEMonitoring]);

  // Stop monitoring
  const stopMonitoring = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    
    setIsMonitoring(false);
  }, []);

  // Calculate stats
  const messageStats: MessageStats = React.useMemo(() => {
    // Expected message types based on comprehensive analysis
    const expectedMessageTypes = [
      'agentthinking', 'toolcall', 'researchfinding', 'heroImage', 'contentcreation',
      'factchecking', 'finalization', 'completion', 'status', 'connected', 
      'initializing', 'keepalive', 'log', 'error', 'progress', 'stepchange',
      'agentdecision', 'taskassignment'
    ];

    const sseTypes: Record<string, number> = {};
    
    sseMessages.forEach(msg => {
      sseTypes[msg.type] = (sseTypes[msg.type] || 0) + 1;
    });
    
    const receivedTypes = new Set(Object.keys(sseTypes));
    const missingTypes = expectedMessageTypes.filter((type: string) => !receivedTypes.has(type));
    
    return {
      sseMessages: sseMessages.length,
      sseTypes,
      expectedTypes: expectedMessageTypes,
      missingTypes
    };
  }, [sseMessages]);

  // Copy comparison report
  const copyComparisonReport = useCallback(async () => {
    const report = `SSE Reception Analysis Report
===================================
Task ID: ${taskId}
Timestamp: ${new Date().toISOString()}

SSE MESSAGE COUNT: ${messageStats.sseMessages}

RECEIVED MESSAGE TYPES:
${Object.entries(messageStats.sseTypes).map(([type, count]) => `  ${type}: ${count}`).join('\n')}

EXPECTED MESSAGE TYPES: ${messageStats.expectedTypes.length}
${messageStats.expectedTypes.map(type => `  ${type}`).join('\n')}

MISSING MESSAGE TYPES: ${messageStats.missingTypes.length}
${messageStats.missingTypes.join(', ') || 'None missing!'}

COVERAGE: ${((messageStats.expectedTypes.length - messageStats.missingTypes.length) / messageStats.expectedTypes.length * 100).toFixed(1)}%

INSTRUCTIONS FOR BACKEND ANALYSIS:
1. Run backend comprehensive_notification_analysis.py to see what backend sends to Redis
2. Run redis_sse_diagnostic.py during live blog generation to monitor Redis channels
3. Compare Redis publication count vs SSE reception count (${messageStats.sseMessages})

DETAILED SSE MESSAGES:
${sseMessages.map(msg => `[${msg.timestamp}] ${msg.type}: ${JSON.stringify(msg.data)}`).join('\n')}
`;

    try {
      await navigator.clipboard.writeText(report);
      alert('✅ SSE analysis report copied to clipboard!');
    } catch (error) {
      logger.error('Failed to copy report', error);
      alert('❌ Failed to copy report');
    }
  }, [taskId, messageStats, sseMessages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopMonitoring();
    };
  }, [stopMonitoring]);

  if (status === 'loading') {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center">Loading authentication...</div>
        </CardContent>
      </Card>
    );
  }

  if (status !== 'authenticated') {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="p-4 bg-yellow-100 dark:bg-yellow-900 border border-yellow-300 rounded-md">
            <p className="text-yellow-800 dark:text-yellow-200">
              Please sign in to test SSE message reception.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-7xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          � SSE Message Reception Analysis
          {isMonitoring && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
              Monitoring
            </span>
          )}
        </CardTitle>
        <CardDescription>
          Monitor SSE message reception and analyze against expected message types. Use backend Python scripts to compare Redis publication.
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Controls */}
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label htmlFor="taskId" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Task ID
            </label>
            <Input
              id="taskId"
              value={taskId}
              onChange={(e) => setTaskId(e.target.value)}
              placeholder="Enter task ID to monitor..."
              disabled={isMonitoring}
            />
          </div>
          <Button
            onClick={isMonitoring ? stopMonitoring : startMonitoring}
            disabled={!taskId.trim() && !isMonitoring}
            className={isMonitoring ? "bg-red-600 hover:bg-red-700" : ""}
          >
            {isMonitoring ? 'Stop Monitoring' : 'Start Monitoring'}
          </Button>
        </div>

        {/* Connection Error */}
        {connectionError && (
          <div className="p-4 bg-red-100 dark:bg-red-900 border border-red-300 rounded-md">
            <p className="text-red-800 dark:text-red-200">{connectionError}</p>
          </div>
        )}

        {/* Backend Analysis Instructions */}
        <div className="p-4 bg-blue-50 dark:bg-blue-900 border border-blue-200 rounded-md">
          <h3 className="font-medium text-blue-800 dark:text-blue-200 mb-2">🔧 Backend Analysis Instructions</h3>
          <div className="text-blue-700 dark:text-blue-300 text-sm space-y-1">
            <p><strong>1. Redis Analysis:</strong> Run <code>python comprehensive_notification_analysis.py</code> in backend to see what&apos;s published to Redis</p>
            <p><strong>2. Live Monitoring:</strong> Run <code>python redis_sse_diagnostic.py {taskId}</code> during blog generation to monitor Redis channels</p>
            <p><strong>3. Compare:</strong> Compare Redis message count vs SSE received count ({messageStats.sseMessages} so far)</p>
          </div>
        </div>

        {/* Message Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-2xl font-bold text-blue-600">{messageStats.sseMessages}</div>
              <div className="text-xs text-gray-600">SSE Messages</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-2xl font-bold text-green-600">{messageStats.expectedTypes.length}</div>
              <div className="text-xs text-gray-600">Expected Types</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-2xl font-bold text-red-600">{messageStats.missingTypes.length}</div>
              <div className="text-xs text-gray-600">Missing Types</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-2xl font-bold text-orange-600">
                {((messageStats.expectedTypes.length - messageStats.missingTypes.length) / messageStats.expectedTypes.length * 100).toFixed(0)}%
              </div>
              <div className="text-xs text-gray-600">Coverage</div>
            </CardContent>
          </Card>
        </div>

        {/* Tab Navigation with Copy Button */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="-mb-px flex justify-between items-center">
            <div className="flex space-x-8">
              {(['comparison', 'sse', 'analysis'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  }`}
                >
                  {tab === 'comparison' && 'Coverage Analysis'}
                  {tab === 'sse' && 'SSE Messages'}
                  {tab === 'analysis' && 'Detailed Analysis'}
                </button>
              ))}
            </div>
            <Button
              onClick={copyComparisonReport}
              size="sm"
              variant="outline"
              className="text-xs"
            >
              📋 Copy Report
            </Button>
          </nav>
        </div>

        {/* Tab Content */}
        <div className="h-[500px] overflow-y-auto border rounded-md p-4">
          {activeTab === 'comparison' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Message Type Coverage</h3>
              
              {messageStats.missingTypes.length > 0 && (
                <div className="p-4 bg-red-50 dark:bg-red-900 border border-red-200 rounded-md">
                  <h4 className="font-medium text-red-800 dark:text-red-200">❌ Missing Message Types ({messageStats.missingTypes.length}):</h4>
                  <p className="text-red-700 dark:text-red-300 text-sm mt-1">{messageStats.missingTypes.join(', ')}</p>
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium text-blue-700">� Received Types ({Object.keys(messageStats.sseTypes).length}):</h4>
                  <div className="space-y-1 mt-2">
                    {Object.entries(messageStats.sseTypes).map(([type, count]) => (
                      <div key={type} className="text-sm flex justify-between">
                        <span>{type}</span>
                        <span className="font-mono">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <h4 className="font-medium text-gray-700">📋 Expected Types ({messageStats.expectedTypes.length}):</h4>
                  <div className="space-y-1 mt-2">
                    {messageStats.expectedTypes.map(type => (
                      <div key={type} className={`text-sm ${
                        messageStats.sseTypes[type] ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {messageStats.sseTypes[type] ? '✅' : '❌'} {type}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'sse' && (
            <div className="space-y-3">
              <h3 className="text-lg font-semibold text-blue-700">🔵 SSE Messages ({messageStats.sseMessages})</h3>
              {sseMessages.length === 0 ? (
                <p className="text-gray-500">No SSE messages received yet...</p>
              ) : (
                sseMessages.map((message) => (
                  <div key={message.id} className="border-b pb-3">
                    <div className="flex justify-between items-start mb-2">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        {message.type}
                      </span>
                      <div className="text-xs text-gray-500">
                        #{message.id} - {new Date(message.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                    <div className="text-sm">
                      <strong>Message:</strong> {message.data.message || 'No message'}
                    </div>
                    {message.latency && (
                      <div className="text-sm">
                        <strong>Latency:</strong> {Math.round(message.latency)}ms
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'analysis' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">📊 Detailed Analysis</h3>
              
              <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-md">
                <h4 className="font-medium mb-2">Reception Summary:</h4>
                <ul className="text-sm space-y-1">
                  <li>• SSE messages received: {messageStats.sseMessages}</li>
                  <li>• Unique message types: {Object.keys(messageStats.sseTypes).length}</li>
                  <li>• Expected message types: {messageStats.expectedTypes.length}</li>
                  <li>• Missing message types: {messageStats.missingTypes.length}</li>
                  <li>• Coverage: {((messageStats.expectedTypes.length - messageStats.missingTypes.length) / messageStats.expectedTypes.length * 100).toFixed(1)}%</li>
                </ul>
              </div>
              
              <div className="p-4 bg-yellow-50 dark:bg-yellow-900 rounded-md">
                <h4 className="font-medium text-yellow-800 dark:text-yellow-200 mb-2">🔍 Next Steps for Analysis:</h4>
                <ol className="text-sm text-yellow-700 dark:text-yellow-300 space-y-1 list-decimal list-inside">
                  <li>Start a blog generation task while monitoring this tool</li>
                  <li>Run <code>python comprehensive_notification_analysis.py</code> in backend</li>
                  <li>Run <code>python redis_sse_diagnostic.py {taskId || 'YOUR_TASK_ID'}</code> during generation</li>
                  <li>Compare Redis publication count vs SSE reception count</li>
                  <li>Identify which message types are lost between Redis and SSE</li>
                </ol>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}