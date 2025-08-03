import { useRef, useCallback, useEffect } from 'react';
import { JobState, SSEUpdate } from '@/types/blog';

export function useSSEConnection() {
  const eventSourceRef = useRef<EventSource | null>(null);
  const completedTasksRef = useRef<Set<string>>(new Set());

  const connectToTaskStream = useCallback(async (
    taskId: string,
    onUpdate: (taskId: string, updates: Partial<JobState>) => void,
    onCompletion: (taskId: string, content: string) => void,
    onError: (taskId: string, error: string) => void
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
      
      console.log('🔌 Connecting to SSE stream:', streamUrl);
      
      const eventSource = new EventSource(streamUrl);
      
      eventSource.onopen = () => {
        console.log('✅ SSE connection established for task:', taskId);
      };
      
      eventSource.onmessage = (event) => {
        try {
          const data: SSEUpdate = JSON.parse(event.data);
          console.log('📡 SSE update received:', data);
          
          switch (data.type) {
            case 'connected':
              console.log('✅ Connected to task stream:', data.task_id);
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
