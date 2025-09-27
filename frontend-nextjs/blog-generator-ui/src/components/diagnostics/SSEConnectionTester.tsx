"use client"

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { useSession } from 'next-auth/react';
import { API_BASE_URL } from '@/config/constants';
import { logger } from '@/lib/logger';
import { VERBOSE_LOGGING_ENABLED } from '@/lib/logger/env';

interface MessageLog {
  id: number;
  timestamp: string;
  type: string;
  data: any;
  rawMessage: string;
  latency?: number;
}

interface ConnectionStats {
  totalMessages: number;
  imageNotifications: number;
  statusUpdates: number;
  errorMessages: number;
  averageLatency: number;
  connectionDuration: number;
}

export function SSEConnectionTester() {
  const { status } = useSession();
  const [taskId, setTaskId] = useState<string>('');
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageLog[]>([]);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'messages' | 'image-events' | 'raw-data'>('messages');
  const [connectionStats, setConnectionStats] = useState<ConnectionStats>({
    totalMessages: 0,
    imageNotifications: 0,
    statusUpdates: 0,
    errorMessages: 0,
    averageLatency: 0,
    connectionDuration: 0
  });

  const eventSourceRef = useRef<EventSource | null>(null);
  const connectionStartTime = useRef<number>(0);
  const messageCounter = useRef<number>(0);
  const latencySum = useRef<number>(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Function to get JWT token
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
      logger.error('❌ Failed to get auth token', error);
      throw error;
    }
  }, []);

  // Function to connect to SSE stream
  const connectToStream = useCallback(async () => {
    if (!taskId.trim()) {
      setConnectionError('Please enter a task ID');
      return;
    }

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      setConnectionError(null);
      setMessages([]);
      setConnectionStats({
        totalMessages: 0,
        imageNotifications: 0,
        statusUpdates: 0,
        errorMessages: 0,
        averageLatency: 0,
        connectionDuration: 0
      });
      
      // Get authentication token
      const token = await getAuthToken();
      const canLogVerbose = VERBOSE_LOGGING_ENABLED && logger.shouldLog('info');

      // Create SSE connection
      const streamUrl = `${API_BASE_URL}/stream/${taskId.trim()}?token=${encodeURIComponent(token)}`;
      if (canLogVerbose) {
        logger.info('🔗 Connecting to SSE stream', { streamUrl });
      }
      
      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;
      connectionStartTime.current = Date.now();
      messageCounter.current = 0;
      latencySum.current = 0;

      // Connection opened
      eventSource.onopen = () => {
        const openCanLogVerbose = VERBOSE_LOGGING_ENABLED && logger.shouldLog('info');
        if (openCanLogVerbose) {
          logger.info('✅ SSE connection established');
        }
        setIsConnected(true);
        setConnectionError(null);
        
        // Start connection duration timer
        intervalRef.current = setInterval(() => {
          if (connectionStartTime.current) {
            const duration = Math.floor((Date.now() - connectionStartTime.current) / 1000);
            setConnectionStats(prev => ({ ...prev, connectionDuration: duration }));
          }
        }, 1000);
      };

      // Message received
      eventSource.onmessage = (event) => {
        const receivedTime = Date.now();
        messageCounter.current++;
        
        try {
          const data = JSON.parse(event.data);
          const messageType = data.message_type || data.type || 'unknown';
          
          // Calculate latency if timestamp is available
          let latency: number | undefined;
          if (data.timestamp) {
            const sentTime = new Date(data.timestamp).getTime();
            latency = receivedTime - sentTime;
            latencySum.current += latency;
          }
          
          // Create message log entry
          const messageLog: MessageLog = {
            id: messageCounter.current,
            timestamp: new Date(receivedTime).toISOString(),
            type: messageType,
            data: data,
            rawMessage: event.data,
            latency: latency
          };
          
          setMessages(prev => [messageLog, ...prev.slice(0, 99)]); // Keep last 100 messages
          
          // Update statistics
          setConnectionStats(prev => {
            const newStats = { ...prev };
            newStats.totalMessages = messageCounter.current;
            newStats.averageLatency = latencySum.current / messageCounter.current;
            
            // Count message types
            if (messageType.toLowerCase().includes('image') || messageType === 'heroImage') {
              newStats.imageNotifications++;
            } else if (messageType.includes('status') || messageType === 'statusUpdate') {
              newStats.statusUpdates++;
            } else if (messageType === 'error' || messageType.includes('error')) {
              newStats.errorMessages++;
            }
            
            return newStats;
          });
          
          const messageCanLogVerbose = VERBOSE_LOGGING_ENABLED && logger.shouldLog('info');
          if (messageCanLogVerbose) {
            logger.info('📩 SSE message received', { messageType, data });
          }
          
        } catch (parseError) {
          logger.error('❌ Failed to parse SSE message', parseError);
          setConnectionError('Failed to parse incoming message');
        }
      };

      // Connection error
      eventSource.onerror = (error) => {
        logger.error('❌ SSE connection error', error);
        setIsConnected(false);
        
        if (eventSource.readyState === EventSource.CLOSED) {
          setConnectionError('Connection was closed by server - check authentication or server logs');
        } else {
          setConnectionError('Network connection failed - check internet connection and server availability');
        }
        
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      };

    } catch (error) {
      logger.error('❌ Failed to create SSE connection', error);
      setConnectionError(error instanceof Error ? error.message : 'Unknown connection error');
      setIsConnected(false);
    }
  }, [taskId, getAuthToken]);

  // Function to disconnect
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
    setConnectionError(null);
    
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  // Function to copy all logs to clipboard
  const copyLogToClipboard = useCallback(async () => {
    try {
      const logContent = messages.map(message => {
        const timestamp = new Date(message.timestamp).toISOString();
        const latencyText = message.latency ? ` (${Math.round(message.latency)}ms)` : '';
        const basicInfo = `[${timestamp}] ${message.type}${latencyText}: ${message.data.message || 'No message'}`;
        const extraInfo = [];
        
        if (message.data.step) extraInfo.push(`Step: ${message.data.step}`);
        if (message.data.progress !== undefined) extraInfo.push(`Progress: ${message.data.progress}%`);
        if (message.data.hero_image_url) extraInfo.push(`Image URL: ${message.data.hero_image_url}`);
        
        const fullInfo = extraInfo.length > 0 ? `${basicInfo}\n  ${extraInfo.join(', ')}` : basicInfo;
        return `${fullInfo}\n  Raw: ${message.rawMessage}`;
      }).reverse().join('\n\n');
      
      const statsHeader = `SSE Connection Test Results
=================================
Total Messages: ${connectionStats.totalMessages}
Image Events: ${connectionStats.imageNotifications}
Status Updates: ${connectionStats.statusUpdates}
Error Messages: ${connectionStats.errorMessages}
Average Latency: ${Math.round(connectionStats.averageLatency)}ms
Connection Duration: ${connectionStats.connectionDuration}s
Task ID: ${taskId}
Timestamp: ${new Date().toISOString()}

=================================
MESSAGE LOG:
=================================

`;
      
      const fullContent = statsHeader + logContent;
      
      await navigator.clipboard.writeText(fullContent);
      
      // Show temporary success message
      const originalText = document.querySelector('.copy-button-text');
      if (originalText) {
        const temp = originalText.textContent;
        originalText.textContent = '✅ Copied!';
        setTimeout(() => {
          originalText.textContent = temp;
        }, 2000);
      }
      
    } catch (error) {
      logger.error('Failed to copy SSE logs to clipboard', error);
      alert('Failed to copy to clipboard. Please manually select and copy the content.');
    }
  }, [messages, connectionStats, taskId]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

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
              Please sign in to test SSE connections.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-6xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          🔗 SSE Connection Tester
          {isConnected && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
              Connected
            </span>
          )}
          {connectionError && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
              Error
            </span>
          )}
        </CardTitle>
        <CardDescription>
          Test Server-Sent Events connection to backend notification system
        </CardDescription>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Connection Controls */}
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
              disabled={isConnected}
            />
          </div>
          <Button
            onClick={isConnected ? disconnect : connectToStream}
            disabled={!taskId.trim() && !isConnected}
            className={isConnected ? "bg-red-600 hover:bg-red-700" : ""}
          >
            {isConnected ? 'Disconnect' : 'Connect'}
          </Button>
        </div>

        {/* Authentication Status */}
        <div className="text-sm text-gray-600 dark:text-gray-400">
          <strong>Auth Token:</strong> {authToken ? '✅ Retrieved' : '❌ None'}
          {authToken && (
            <span className="ml-2 font-mono text-xs">
              {authToken.substring(0, 20)}...
            </span>
          )}
        </div>

        {/* Connection Error */}
        {connectionError && (
          <div className="p-4 bg-red-100 dark:bg-red-900 border border-red-300 rounded-md">
            <p className="text-red-800 dark:text-red-200">{connectionError}</p>
          </div>
        )}

        {/* Statistics */}
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-2xl font-bold">{connectionStats.totalMessages}</div>
              <div className="text-xs text-gray-600">Total Messages</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-2xl font-bold text-blue-600">{connectionStats.imageNotifications}</div>
              <div className="text-xs text-gray-600">Image Events</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-2xl font-bold text-green-600">{connectionStats.statusUpdates}</div>
              <div className="text-xs text-gray-600">Status Updates</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-2xl font-bold text-red-600">{connectionStats.errorMessages}</div>
              <div className="text-xs text-gray-600">Errors</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-2xl font-bold">{Math.round(connectionStats.averageLatency)}ms</div>
              <div className="text-xs text-gray-600">Avg Latency</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-3 text-center">
              <div className="text-2xl font-bold">{connectionStats.connectionDuration}s</div>
              <div className="text-xs text-gray-600">Connected</div>
            </CardContent>
          </Card>
        </div>

        {/* Tab Navigation with Copy Button */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="-mb-px flex justify-between items-center">
            <div className="flex space-x-8">
              {(['messages', 'image-events', 'raw-data'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                  }`}
                >
                  {tab === 'messages' && 'Message Log'}
                  {tab === 'image-events' && 'Image Events'}
                  {tab === 'raw-data' && 'Raw Data'}
                </button>
              ))}
            </div>
            <Button
              onClick={() => copyLogToClipboard()}
              size="sm"
              variant="outline"
              className="text-xs"
            >
              <span className="copy-button-text">📋 Copy All Logs</span>
            </Button>
          </nav>
        </div>

        {/* Message Content */}
        <div className="h-[400px] overflow-y-auto border rounded-md p-4">
          {activeTab === 'messages' && (
            <>
              {messages.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  No messages received yet...
                </div>
              ) : (
                <div className="space-y-3">
                  {messages.map((message) => (
                    <div key={message.id} className="border-b pb-3">
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                            {message.type}
                          </span>
                          {message.latency && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                              {Math.round(message.latency)}ms
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                      <div className="text-sm">
                        <strong>Message:</strong> {message.data.message || 'No message'}
                      </div>
                      {message.data.step && (
                        <div className="text-sm">
                          <strong>Step:</strong> {message.data.step}
                        </div>
                      )}
                      {message.data.progress !== undefined && (
                        <div className="text-sm">
                          <strong>Progress:</strong> {message.data.progress}%
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {activeTab === 'image-events' && (
            <>
              {messages.filter(m => m.type.toLowerCase().includes('image') || m.type === 'heroImage').length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  No image events received yet...
                </div>
              ) : (
                <div className="space-y-3">
                  {messages
                    .filter(m => m.type.toLowerCase().includes('image') || m.type === 'heroImage')
                    .map((message) => (
                    <div key={message.id} className="border-b pb-3">
                      <div className="flex justify-between items-start mb-2">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                          {message.type}
                        </span>
                        <div className="text-xs text-gray-500">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                      <div className="text-sm">
                        <strong>Message:</strong> {message.data.message || 'Image event'}
                      </div>
                      {message.data.hero_image_url && (
                        <div className="text-sm">
                          <strong>Image URL:</strong> 
                          <a href={message.data.hero_image_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline ml-1">
                            {message.data.hero_image_url.substring(0, 50)}...
                          </a>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {activeTab === 'raw-data' && (
            <>
              {messages.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  No raw data available...
                </div>
              ) : (
                <div className="space-y-3">
                  {messages.map((message) => (
                    <div key={message.id} className="border-b pb-3">
                      <div className="flex justify-between items-start mb-2">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                          {message.type}
                        </span>
                        <div className="text-xs text-gray-500">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                      <pre className="text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded overflow-x-auto">
                        {JSON.stringify(message.data, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}