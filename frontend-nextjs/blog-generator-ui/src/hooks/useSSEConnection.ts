import { useRef, useCallback, useEffect } from 'react';
import { JobState, SSEUpdate, LogEntry } from '@/types/blog';

export function useSSEConnection() {
  const eventSourceRef = useRef<EventSource | null>(null);
  const completedTasksRef = useRef<Set<string>>(new Set());

  const connectToTaskStream = useCallback(async (
    taskId: string,
    onUpdate: (taskId: string, updates: Partial<JobState>) => void,
    onCompletion: (taskId: string, content: string) => void,
    onError: (taskId: string, error: string) => void,
    onLogUpdate?: (taskId: string, log: LogEntry) => void
  ): Promise<EventSource> => {
    try {
      // Get JWT token for SSE authentication
      const tokenResponse = await fetch('/api/auth/jwt-token', {
        method: 'GET',
        credentials: 'include'
      });
      
      if (!tokenResponse.ok) {
        throw new Error('Failed to get authentication token');
      }
      
      const { token } = await tokenResponse.json();
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'https://localhost:5000';
      const streamUrl = `${backendUrl}/stream/${taskId}?token=${encodeURIComponent(token)}`;
      
      const eventSource = new EventSource(streamUrl);
      
      eventSource.onmessage = (event) => {
        try {
          const data: SSEUpdate = JSON.parse(event.data);
          
          // Handle the actual SSE message format from the backend
          if (data.status && data.step && data.timestamp) {
            // Update job status and step
            onUpdate(taskId, {
              status: data.status as JobState['status'],
              currentStep: data.step,
              progress: data.progress || (data.status === 'in_progress' ? 50 : 0)
            });
            
            // Add log entry
            if (onLogUpdate) {
              onLogUpdate(taskId, {
                timestamp: data.timestamp,
                step: data.step,
                message: data.step,
                progress: data.progress || 0
              });
            }
            
            // Handle completion
            if (data.status === 'completed' && data.result) {
              if (!completedTasksRef.current.has(taskId)) {
                completedTasksRef.current.add(taskId);
                onCompletion(taskId, data.result);
              }
              eventSource.close();
            }
            
            // Handle errors  
            if (data.status === 'failed' && data.error) {
              onError(taskId, data.error);
              eventSource.close();
            }
            return;
          }
          
          // Fallback: handle structured messages with type field (if any)
          switch (data.type) {
            case 'connected':
              console.log('✅ Connected to task stream:', data.task_id);
              break;
              
            case 'log_update':
              console.log('📋 Log update:', data);
              if (onLogUpdate && data.step && data.message && data.timestamp) {
                onLogUpdate(data.task_id, {
                  timestamp: data.timestamp,
                  step: data.step,
                  message: data.message,
                  progress: data.progress || 0
                });
              }
              break;
              
            case 'status_update':
              console.log('📝 Status update:', data);
              onUpdate(data.task_id, {
                status: data.status as JobState['status'],
                currentStep: data.current_step || 'Processing...',
                progress: Math.round((data.progress || 0) * 100)
              });
              
              // Handle completion
              if (data.status === 'completed' && data.result) {
                if (!completedTasksRef.current.has(data.task_id)) {
                  completedTasksRef.current.add(data.task_id);
                  onCompletion(data.task_id, data.result);
                }
                eventSource.close();
              }
              
              // Handle errors  
              if (data.status === 'failed' && data.error) {
                onError(data.task_id, data.error);
                eventSource.close();
              }
              break;
              
            case 'stream_ended':
              console.log('🏁 Stream ended for task:', data.task_id);
              eventSource.close();
              break;
              
            case 'error':
              console.error('❌ Stream error:', data.message);
              break;
          }
        } catch (error) {
          console.error('Failed to parse SSE data:', error);
        }
      };
      
      eventSource.onerror = (error) => {
        console.error('❌ SSE connection error:', error);
        eventSource.close();
      };
      
      return eventSource;
      
    } catch (error) {
      console.error('Failed to create SSE connection:', error);
      throw error;
    }
  }, []);

  const closeConnection = useCallback(() => {
    if (eventSourceRef.current) {
      console.log('🔌 Closing SSE connection');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => closeConnection();
  }, [closeConnection]);

  return {
    connectToTaskStream,
    closeConnection,
    eventSourceRef,
    completedTasksRef
  };
}
