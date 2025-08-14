import { useRef, useCallback, useEffect } from 'react';
import { API_BASE_URL } from '@/config/constants';
import { JobState, LogEntry } from '@/types/blog';

interface WebSocketMessage {
  type: string;
  task_id?: string;
  data?: any;
  timestamp?: string;
}

interface WebSocketUpdate {
  status?: string;
  step?: string;
  progress?: number;
  hero_image_url?: string;
  content?: string;
  error?: string;
}

export function useWebSocketConnection() {
  const websocketRef = useRef<WebSocket | null>(null);
  const completedTasksRef = useRef<Set<string>>(new Set());
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const maxReconnectAttempts = 5;
  const baseReconnectDelay = 1000; // 1 second

  const connectToTaskStream = useCallback(async (
    taskId: string,
    onUpdate: (taskId: string, updates: Partial<JobState>) => void,
    onCompletion: (taskId: string, content: string, heroImageUrl?: string) => void,
    onError: (taskId: string, error: string) => void,
    onLogUpdate?: (taskId: string, log: LogEntry) => void
  ): Promise<WebSocket | null> => {
    try {
      // Close any existing connection first
      if (websocketRef.current) {
        try { 
          websocketRef.current.close(1000, 'New connection requested'); 
        } catch {}
        websocketRef.current = null;
      }

      // Clear any pending reconnection attempts
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      const tokenResponse = await fetch('/api/auth/jwt-token', {
        method: 'GET',
        credentials: 'include'
      });
      if (!tokenResponse.ok) throw new Error('Failed to get authentication token');
      const { token } = await tokenResponse.json();
      
      // Use WebSocket instead of EventSource
      const wsUrl = `${API_BASE_URL.replace('http', 'ws')}/ws/${taskId}?token=${encodeURIComponent(token)}`;
      const websocket = new WebSocket(wsUrl);
      websocketRef.current = websocket;

      // Connection opened
      websocket.onopen = () => {
        console.log(`WebSocket connected for task ${taskId}`);
        reconnectAttemptsRef.current = 0; // Reset reconnection attempts on successful connection
      };

      // Handle messages
      websocket.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          switch (message.type) {
            case 'connected':
              console.log('WebSocket connection confirmed');
              break;
              
            case 'task_update':
              if (message.data && message.task_id === taskId) {
                const data: WebSocketUpdate = message.data;
                
                // Update job state
                onUpdate(taskId, {
                  status: data.status as JobState['status'],
                  currentStep: data.step || 'Processing...',
                  progress: data.progress || (data.status === 'in_progress' ? 50 : 0)
                });

                // Log update if handler provided
                if (onLogUpdate && data.step && message.timestamp) {
                  onLogUpdate(taskId, {
                    timestamp: message.timestamp,
                    step: data.step,
                    message: data.step,
                    progress: data.progress || 0
                  });
                }

                // Handle completion
                if (data.status === 'completed' && data.content) {
                  if (!completedTasksRef.current.has(taskId)) {
                    completedTasksRef.current.add(taskId);
                    onCompletion(taskId, data.content, data.hero_image_url);
                  }
                  websocket.close(1000, 'Task completed');
                }

                // Handle failure
                if (data.status === 'failed' && data.error) {
                  onError(taskId, data.error);
                  websocket.close(1000, 'Task failed');
                }
              }
              break;
              
            case 'pong':
              // Heartbeat response - connection is alive
              break;
              
            case 'error':
              console.error('WebSocket error message:', message.data);
              if (message.data?.message) {
                onError(taskId, message.data.message);
              }
              break;
              
            default:
              console.log('Unknown WebSocket message type:', message.type);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      // Handle connection errors
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        onError(taskId, 'WebSocket connection error');
      };

      // Handle connection close
      websocket.onclose = (event) => {
        console.log(`WebSocket closed for task ${taskId}:`, event.code, event.reason);
        
        // Only attempt reconnection for unexpected closures (not manual close codes)
        if (event.code !== 1000 && event.code !== 1001 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = baseReconnectDelay * Math.pow(2, reconnectAttemptsRef.current);
          reconnectAttemptsRef.current++;
          
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`Reconnecting WebSocket for task ${taskId}`);
            connectToTaskStream(taskId, onUpdate, onCompletion, onError, onLogUpdate);
          }, delay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          console.error(`Max reconnection attempts reached for task ${taskId}`);
          onError(taskId, 'Connection lost - please refresh the page');
        }
      };

      return websocket;
      
    } catch (error) {
      console.error('Failed to establish WebSocket connection:', error);
      onError(taskId, `Failed to connect: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return null;
    }
  }, []);

  const closeConnection = useCallback(() => {
    if (websocketRef.current) {
      try {
        websocketRef.current.close(1000, 'Manual close');
      } catch {}
      websocketRef.current = null;
    }
    
    // Clear reconnection attempts
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectAttemptsRef.current = 0;
  }, []);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
      websocketRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  const sendPing = useCallback(() => {
    return sendMessage({ type: 'ping' });
  }, [sendMessage]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      closeConnection();
    };
  }, [closeConnection]);

  // Periodic ping to keep connection alive
  useEffect(() => {
    const pingInterval = setInterval(() => {
      if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
        sendPing();
      }
    }, 30000); // Ping every 30 seconds

    return () => clearInterval(pingInterval);
  }, [sendPing]);

  return {
    connectToTaskStream,
    closeConnection,
    sendMessage,
    sendPing,
    completedTasksRef,
    isConnected: websocketRef.current?.readyState === WebSocket.OPEN
  };
}
