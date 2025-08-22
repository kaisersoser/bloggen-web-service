import { useState, useEffect, useCallback, useRef } from 'react';
import { useSession } from 'next-auth/react';

export interface SSEConnectionOptions {
  maxRetries?: number;
  retryDelay?: number;
  timeoutMs?: number;
}

export interface SSEConnectionState {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  retryCount: number;
}

export interface SSEMessage {
  type: string;
  data: any;
  timestamp: string;
}

export function useEnhancedSSEConnection(
  taskId: string | null,
  onMessage: (message: SSEMessage) => void,
  options: SSEConnectionOptions = {}
) {
  const { data: session, status } = useSession();
  const [connectionState, setConnectionState] = useState<SSEConnectionState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    retryCount: 0
  });

  const eventSourceRef = useRef<EventSource | null>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const connectionTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const {
    maxRetries = 5,
    retryDelay = 2000,
    timeoutMs = 30000
  } = options;

  // Clean up function
  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
      connectionTimeoutRef.current = null;
    }
  }, []);

  // Get JWT token for SSE authentication
  const getJWTToken = useCallback(async (): Promise<string | null> => {
    try {
      if (status !== 'authenticated' || !session) {
        throw new Error('No authenticated session available');
      }

      const response = await fetch('/api/auth/jwt-token');
      
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Session expired - please sign in again');
        }
        throw new Error(`JWT token request failed: ${response.status}`);
      }

      const data = await response.json();
      if (!data.token) {
        throw new Error('No JWT token received from server');
      }

      return data.token;
    } catch (error) {
      console.error('JWT token retrieval failed:', error);
      throw error;
    }
  }, [session, status]);

  // Connect to SSE stream
  const connect = useCallback(async () => {
    if (!taskId || connectionState.isConnecting || connectionState.isConnected) {
      return;
    }

    // Check authentication first
    if (status !== 'authenticated' || !session) {
      setConnectionState(prev => ({
        ...prev,
        error: 'Please sign in to connect to the stream',
        isConnecting: false
      }));
      return;
    }

    setConnectionState(prev => ({
      ...prev,
      isConnecting: true,
      error: null
    }));

    try {
      // Get fresh JWT token
      const token = await getJWTToken();
      if (!token) {
        throw new Error('Failed to obtain authentication token');
      }

      // Create SSE connection with authentication
      const streamUrl = `${process.env.NEXT_PUBLIC_BACKEND_URL}/stream/${taskId}?token=${encodeURIComponent(token)}`;
      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;

      // Set connection timeout
      connectionTimeoutRef.current = setTimeout(() => {
        if (!connectionState.isConnected) {
          cleanup();
          setConnectionState(prev => ({
            ...prev,
            isConnecting: false,
            error: 'Connection timeout - please check your internet connection and try again'
          }));
        }
      }, timeoutMs);

      // Handle successful connection
      eventSource.onopen = () => {
        console.log('✅ SSE connection established');
        if (connectionTimeoutRef.current) {
          clearTimeout(connectionTimeoutRef.current);
          connectionTimeoutRef.current = null;
        }
        setConnectionState(prev => ({
          ...prev,
          isConnected: true,
          isConnecting: false,
          error: null,
          retryCount: 0
        }));
      };

      // Handle incoming messages
      eventSource.onmessage = (event) => {
        try {
          const message: SSEMessage = JSON.parse(event.data);
          onMessage(message);
        } catch (error) {
          console.error('Failed to parse SSE message:', error);
        }
      };

      // Handle connection errors with smart retry logic
      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        cleanup();

        const isAuthError = eventSource.readyState === EventSource.CLOSED;
        const shouldRetry = connectionState.retryCount < maxRetries;

        if (isAuthError) {
          setConnectionState(prev => ({
            ...prev,
            isConnected: false,
            isConnecting: false,
            error: 'Authentication failed - please sign out and sign back in',
            retryCount: prev.retryCount + 1
          }));
        } else if (shouldRetry) {
          // Exponential backoff retry
          const delay = retryDelay * Math.pow(2, connectionState.retryCount);
          
          setConnectionState(prev => ({
            ...prev,
            isConnected: false,
            isConnecting: false,
            error: `Connection lost. Retrying in ${Math.ceil(delay / 1000)}s... (${prev.retryCount + 1}/${maxRetries})`,
            retryCount: prev.retryCount + 1
          }));

          retryTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          setConnectionState(prev => ({
            ...prev,
            isConnected: false,
            isConnecting: false,
            error: 'Connection failed after multiple attempts. Please refresh the page and try again.'
          }));
        }
      };

    } catch (error) {
      cleanup();
      const errorMessage = error instanceof Error ? error.message : 'Unknown connection error';
      setConnectionState(prev => ({
        ...prev,
        isConnecting: false,
        error: errorMessage
      }));
    }
  }, [taskId, session, status, connectionState.isConnecting, connectionState.isConnected, connectionState.retryCount, getJWTToken, onMessage, maxRetries, retryDelay, timeoutMs, cleanup]);

  // Disconnect from SSE stream
  const disconnect = useCallback(() => {
    cleanup();
    setConnectionState({
      isConnected: false,
      isConnecting: false,
      error: null,
      retryCount: 0
    });
  }, [cleanup]);

  // Auto-connect when taskId changes and user is authenticated
  useEffect(() => {
    if (taskId && status === 'authenticated') {
      connect();
    } else {
      disconnect();
    }

    return cleanup;
  }, [taskId, status, connect, disconnect, cleanup]);

  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return {
    ...connectionState,
    connect,
    disconnect,
    retry: () => {
      setConnectionState(prev => ({ ...prev, retryCount: 0 }));
      connect();
    }
  };
}
