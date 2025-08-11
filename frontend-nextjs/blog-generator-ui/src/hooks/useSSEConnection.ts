import { useRef, useCallback, useEffect } from 'react';
import { API_BASE_URL } from '@/config/constants';
import { JobState, SSEUpdate, LogEntry } from '@/types/blog';

export function useSSEConnection() {
  const eventSourceRef = useRef<EventSource | null>(null);
  const completedTasksRef = useRef<Set<string>>(new Set());

  const connectToTaskStream = useCallback(async (
    taskId: string,
    onUpdate: (taskId: string, updates: Partial<JobState>) => void,
    onCompletion: (taskId: string, content: string, heroImageUrl?: string) => void,
    onError: (taskId: string, error: string) => void,
    onLogUpdate?: (taskId: string, log: LogEntry) => void
  ): Promise<EventSource> => {
    try {
      // Close any existing connection first
      if (eventSourceRef.current) {
        try { eventSourceRef.current.close(); } catch {}
        eventSourceRef.current = null;
      }

      const tokenResponse = await fetch('/api/auth/jwt-token', {
        method: 'GET',
        credentials: 'include'
      });
      if (!tokenResponse.ok) throw new Error('Failed to get authentication token');
      const { token } = await tokenResponse.json();
      const streamUrl = `${API_BASE_URL}/stream/${taskId}?token=${encodeURIComponent(token)}`;
      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        try {
          const data: SSEUpdate = JSON.parse(event.data);

            // Direct/basic format (status + step)
          if (data.status && data.step && data.timestamp) {
            onUpdate(taskId, {
              status: data.status as JobState['status'],
              currentStep: data.step,
              progress: data.progress || (data.status === 'in_progress' ? 50 : 0)
            });
            if (onLogUpdate) {
              onLogUpdate(taskId, {
                timestamp: data.timestamp,
                step: data.step,
                message: data.step,
                progress: data.progress || 0
              });
            }
      if (data.status === 'completed' && data.result) {
              if (!completedTasksRef.current.has(taskId)) {
                completedTasksRef.current.add(taskId);
        onCompletion(taskId, data.result, (data as any).hero_image_url);
              }
              eventSource.close();
            }
            if (data.status === 'failed' && data.error) {
              onError(taskId, data.error);
              eventSource.close();
            }
            return;
          }

          // Structured type field format
          switch (data.type) {
            case 'connected':
              break;
            case 'log_update':
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
              onUpdate(data.task_id, {
                status: data.status as JobState['status'],
                currentStep: data.current_step || 'Processing...',
                progress: Math.round((data.progress || 0) * 100)
              });
              if (data.status === 'completed' && data.result) {
                if (!completedTasksRef.current.has(data.task_id)) {
                  completedTasksRef.current.add(data.task_id);
                  onCompletion(data.task_id, data.result);
                }
                eventSource.close();
              }
              if (data.status === 'failed' && data.error) {
                onError(data.task_id, data.error);
                eventSource.close();
              }
              break;
            case 'stream_ended':
              eventSource.close();
              break;
            case 'error':
              console.error('Stream error:', data.message);
              break;
          }
        } catch (err) {
          console.error('Failed to parse SSE data:', err);
        }
      };

      eventSource.onerror = (err) => {
        console.error('SSE connection error:', err);
        try { eventSource.close(); } catch {}
        if (eventSourceRef.current === eventSource) {
          eventSourceRef.current = null;
        }
      };

      return eventSource;
    } catch (err) {
      console.error('Failed to create SSE connection:', err);
      throw err;
    }
  }, []);

  const closeConnection = useCallback(() => {
    if (eventSourceRef.current) {
      try { eventSourceRef.current.close(); } catch {}
      eventSourceRef.current = null;
    }
  }, []);

  useEffect(() => () => closeConnection(), [closeConnection]);

  return { connectToTaskStream, closeConnection, eventSourceRef, completedTasksRef };
}
