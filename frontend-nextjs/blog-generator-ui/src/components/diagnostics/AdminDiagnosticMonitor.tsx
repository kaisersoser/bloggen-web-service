"use client"

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useSession } from 'next-auth/react';
import { API_BASE_URL } from '@/config/constants';
import { ChevronDown, ChevronUp, Monitor, Copy, X } from 'lucide-react';

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
  coverage: number;
}

interface AdminDiagnosticMonitorProps {
  currentJobId: string | null;
  isGenerating: boolean;
}

export function AdminDiagnosticMonitor({ currentJobId, isGenerating }: AdminDiagnosticMonitorProps) {
  const { data: session } = useSession();
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [isMonitoring, setIsMonitoring] = useState<boolean>(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [sseMessages, setSSEMessages] = useState<SSEMessage[]>([]);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'stats' | 'messages' | 'analysis'>('stats');
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const messageCounterRef = useRef<number>(0);

  // Expected message types based on comprehensive analysis
  const expectedMessageTypes = [
    'agentthinking', 'toolcall', 'researchfinding', 'heroImage', 'contentcreation',
    'factchecking', 'finalization', 'completion', 'status', 'connected', 
    'initializing', 'keepalive', 'log', 'error', 'progress', 'stepchange',
    'agentdecision', 'taskassignment'
  ];

  // Only show for Admin users
  if (!session || session.user?.role !== 'ADMIN') {
    return null;
  }

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
      
      setAuthToken(token);
      return token;
    } catch (error) {
      console.error('❌ Failed to get auth token:', error);
      throw error;
    }
  }, []);

  // Start SSE monitoring
  const startSSEMonitoring = useCallback(async (taskId: string, token: string) => {
    try {
      const streamUrl = `${API_BASE_URL}/stream/${taskId}?token=${encodeURIComponent(token)}`;
      console.log('🔗 Admin diagnostic monitoring:', streamUrl);
      
      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('✅ Admin SSE monitoring connection established');
        setConnectionError(null);
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
          
          setSSEMessages(prev => [sseMessage, ...prev.slice(0, 49)]); // Keep last 50 messages
          console.log('🔍 Admin monitoring - SSE message:', messageType, data);
          
        } catch (parseError) {
          console.error('❌ Failed to parse SSE message:', parseError);
        }
      };

      eventSource.onerror = (error) => {
        console.error('❌ Admin SSE monitoring error:', error);
        setConnectionError('SSE monitoring connection failed');
      };

    } catch (error) {
      console.error('❌ Failed to start admin SSE monitoring:', error);
      setConnectionError(error instanceof Error ? error.message : 'Unknown monitoring error');
    }
  }, []);

  // Start monitoring (DISABLED FOR REDIS-SSE BRIDGE FIX)
  const startMonitoring = useCallback(async () => {
    if (!currentJobId) {
      setConnectionError('No active blog generation to monitor');
      return;
    }

    // TEMPORARY DISABLE: Our new immediate SSE connection system handles monitoring
    // This prevents dual SSE connections from conflicting
    console.log('⚠️ Admin monitoring disabled - using enhanced SSE system instead');
    setConnectionError('Admin monitoring disabled - enhanced SSE active');
    return;
    
    /* ORIGINAL CODE DISABLED:
    try {
      setConnectionError(null);
      setSSEMessages([]);
      messageCounterRef.current = 0;
      
      const token = await getAuthToken();
      await startSSEMonitoring(currentJobId, token);
      setIsMonitoring(true);
      
    } catch (error) {
      console.error('❌ Failed to start admin monitoring:', error);
      setConnectionError(error instanceof Error ? error.message : 'Unknown connection error');
    }
    */
  }, [currentJobId, getAuthToken, startSSEMonitoring]);

  // Stop monitoring
  const stopMonitoring = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    
    setIsMonitoring(false);
  }, []);

  // Auto-stop monitoring when generation ends
  useEffect(() => {
    if (!isGenerating && isMonitoring) {
      stopMonitoring();
    }
  }, [isGenerating, isMonitoring, stopMonitoring]);

  // CRITICAL FIX: Reset state when task ID changes to prevent stale data
  useEffect(() => {
    // Clear previous task's data when switching to a new task
    setSSEMessages([]);
    messageCounterRef.current = 0;
    setConnectionError(null);
    console.log('🔄 Admin diagnostic: Reset state for new task ID:', currentJobId);
  }, [currentJobId]);

  // Calculate stats
  const messageStats: MessageStats = React.useMemo(() => {
    const sseTypes: Record<string, number> = {};
    
    sseMessages.forEach(msg => {
      sseTypes[msg.type] = (sseTypes[msg.type] || 0) + 1;
    });
    
    const receivedTypes = new Set(Object.keys(sseTypes));
    const missingTypes = expectedMessageTypes.filter(type => !receivedTypes.has(type));
    const coverage = ((expectedMessageTypes.length - missingTypes.length) / expectedMessageTypes.length * 100);
    
    return {
      sseMessages: sseMessages.length,
      sseTypes,
      expectedTypes: expectedMessageTypes,
      missingTypes,
      coverage
    };
  }, [sseMessages]);

  // Copy analysis report
  const copyAnalysisReport = useCallback(async () => {
    const report = `Admin Diagnostic Report - SSE Monitoring
==========================================
Task ID: ${currentJobId}
Generation Status: ${isGenerating ? 'Active' : 'Completed'}
Monitoring Status: ${isMonitoring ? 'Active' : 'Stopped'}
Timestamp: ${new Date().toISOString()}

MESSAGE STATISTICS:
- Total SSE Messages: ${messageStats.sseMessages}
- Unique Message Types: ${Object.keys(messageStats.sseTypes).length}
- Expected Message Types: ${messageStats.expectedTypes.length}
- Missing Message Types: ${messageStats.missingTypes.length}
- Coverage: ${messageStats.coverage.toFixed(1)}%

RECEIVED MESSAGE TYPES:
${Object.entries(messageStats.sseTypes).map(([type, count]) => `  ${type}: ${count}`).join('\n')}

MISSING MESSAGE TYPES:
${messageStats.missingTypes.join(', ') || 'None missing!'}

BACKEND ANALYSIS COMMANDS:
cd backend && source .venv/bin/activate
python src/tests/comprehensive_notification_analysis.py
python src/tests/redis_sse_diagnostic.py ${currentJobId}

DETAILED MESSAGES:
${sseMessages.slice(0, 20).map(msg => `[${msg.timestamp}] ${msg.type}: ${JSON.stringify(msg.data)}`).join('\n')}
${sseMessages.length > 20 ? `... and ${sseMessages.length - 20} more messages` : ''}
`;

    try {
      await navigator.clipboard.writeText(report);
      alert('✅ Admin diagnostic report copied to clipboard!');
    } catch (error) {
      console.error('Failed to copy report:', error);
      alert('❌ Failed to copy report');
    }
  }, [currentJobId, isGenerating, isMonitoring, messageStats, sseMessages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopMonitoring();
    };
  }, [stopMonitoring]);

  return (
    <Card className="w-full border-amber-200 bg-amber-50 dark:bg-amber-950 dark:border-amber-800">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Monitor className="h-4 w-4 text-amber-600" />
            <CardTitle className="text-sm text-amber-800 dark:text-amber-200">
              Admin Diagnostic Monitor
            </CardTitle>
            {isMonitoring && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                Monitoring Active
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {currentJobId && (
              <Button
                onClick={isMonitoring ? stopMonitoring : startMonitoring}
                disabled={!isGenerating && !isMonitoring}
                size="sm"
                variant={isMonitoring ? "destructive" : "default"}
                className="text-xs"
              >
                {isMonitoring ? 'Stop Monitor' : 'Start Monitor'}
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-amber-600 hover:text-amber-700"
            >
              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </div>
        </div>
        <CardDescription className="text-xs text-amber-700 dark:text-amber-300">
          {currentJobId ? (
            <>Monitor SSE message flow for task: <code className="bg-amber-100 dark:bg-amber-900 px-1 rounded">{currentJobId}</code></>
          ) : (
            'Start a blog generation to enable monitoring'
          )}
        </CardDescription>
      </CardHeader>

      {isExpanded && (
        <CardContent className="pt-0 space-y-4">
          {/* Connection Error */}
          {connectionError && (
            <div className="p-3 bg-red-100 dark:bg-red-900 border border-red-300 rounded-md">
              <p className="text-red-800 dark:text-red-200 text-sm">{connectionError}</p>
            </div>
          )}

          {/* Quick Stats */}
          <div className="grid grid-cols-4 gap-3">
            <div className="text-center p-2 bg-white dark:bg-gray-800 rounded border">
              <div className="text-lg font-bold text-blue-600">{messageStats.sseMessages}</div>
              <div className="text-xs text-gray-600">Messages</div>
            </div>
            <div className="text-center p-2 bg-white dark:bg-gray-800 rounded border">
              <div className="text-lg font-bold text-green-600">{Object.keys(messageStats.sseTypes).length}</div>
              <div className="text-xs text-gray-600">Types</div>
            </div>
            <div className="text-center p-2 bg-white dark:bg-gray-800 rounded border">
              <div className="text-lg font-bold text-red-600">{messageStats.missingTypes.length}</div>
              <div className="text-xs text-gray-600">Missing</div>
            </div>
            <div className="text-center p-2 bg-white dark:bg-gray-800 rounded border">
              <div className="text-lg font-bold text-orange-600">{messageStats.coverage.toFixed(0)}%</div>
              <div className="text-xs text-gray-600">Coverage</div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="border-b border-amber-200">
            <nav className="-mb-px flex justify-between items-center">
              <div className="flex space-x-4">
                {(['stats', 'messages', 'analysis'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`py-1 px-2 border-b-2 font-medium text-xs ${
                      activeTab === tab
                        ? 'border-amber-500 text-amber-600 dark:text-amber-400'
                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }`}
                  >
                    {tab === 'stats' && 'Overview'}
                    {tab === 'messages' && 'Live Messages'}
                    {tab === 'analysis' && 'Analysis'}
                  </button>
                ))}
              </div>
              <Button
                onClick={copyAnalysisReport}
                size="sm"
                variant="outline"
                className="text-xs"
              >
                <Copy className="h-3 w-3 mr-1" />
                Copy Report
              </Button>
            </nav>
          </div>

          {/* Tab Content */}
          <div className="max-h-64 overflow-y-auto">
            {activeTab === 'stats' && (
              <div className="space-y-3">
                {messageStats.missingTypes.length > 0 && (
                  <div className="p-3 bg-red-50 dark:bg-red-900 border border-red-200 rounded">
                    <h4 className="font-medium text-red-800 dark:text-red-200 text-sm">Missing Types ({messageStats.missingTypes.length}):</h4>
                    <p className="text-red-700 dark:text-red-300 text-xs mt-1">{messageStats.missingTypes.join(', ')}</p>
                  </div>
                )}
                
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-white dark:bg-gray-800 rounded border">
                    <h4 className="font-medium text-sm mb-2">Received Types</h4>
                    <div className="space-y-1 text-xs">
                      {Object.entries(messageStats.sseTypes).map(([type, count]) => (
                        <div key={type} className="flex justify-between">
                          <span>{type}</span>
                          <span className="font-mono">{count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="p-3 bg-white dark:bg-gray-800 rounded border">
                    <h4 className="font-medium text-sm mb-2">Backend Commands</h4>
                    <div className="space-y-1 text-xs font-mono text-gray-600">
                      <div>comprehensive_notification_analysis.py</div>
                      <div>redis_sse_diagnostic.py {currentJobId}</div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'messages' && (
              <div className="space-y-2">
                {sseMessages.length === 0 ? (
                  <p className="text-gray-500 text-sm text-center py-4">No messages received yet...</p>
                ) : (
                  sseMessages.slice(0, 10).map((message) => (
                    <div key={message.id} className="p-2 bg-white dark:bg-gray-800 rounded border text-xs">
                      <div className="flex justify-between items-start">
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                          {message.type}
                        </span>
                        <span className="text-gray-500">#{message.id}</span>
                      </div>
                      <div className="mt-1 text-gray-700 dark:text-gray-300">
                        {message.data.message || JSON.stringify(message.data).slice(0, 100)}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}

            {activeTab === 'analysis' && (
              <div className="space-y-3">
                <div className="p-3 bg-white dark:bg-gray-800 rounded border">
                  <h4 className="font-medium text-sm mb-2">Analysis Summary</h4>
                  <ul className="text-xs space-y-1 text-gray-600">
                    <li>• Messages received: {messageStats.sseMessages}</li>
                    <li>• Unique types: {Object.keys(messageStats.sseTypes).length}/{messageStats.expectedTypes.length}</li>
                    <li>• Coverage: {messageStats.coverage.toFixed(1)}%</li>
                    <li>• Missing types: {messageStats.missingTypes.length}</li>
                  </ul>
                </div>
                
                <div className="p-3 bg-blue-50 dark:bg-blue-900 rounded border">
                  <h4 className="font-medium text-blue-800 dark:text-blue-200 text-sm mb-2">Next Steps</h4>
                  <ol className="text-xs text-blue-700 dark:text-blue-300 space-y-1 list-decimal list-inside">
                    <li>Copy this report for detailed analysis</li>
                    <li>Run backend Redis diagnostic scripts</li>
                    <li>Compare Redis publication vs SSE reception</li>
                    <li>Identify message filtering or subscription issues</li>
                  </ol>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      )}
    </Card>
  );
}