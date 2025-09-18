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
      
      console.log('🔗 Attempting SSE connection to:', streamUrl);
      console.log('🔗 Task ID:', taskId);
      
      const eventSource = new EventSource(streamUrl);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('✅ SSE connection established for task', taskId);
        console.log('✅ EventSource readyState:', eventSource.readyState);
      };

      eventSource.onmessage = (event) => {
        try {
          const data: SSEUpdate = JSON.parse(event.data);
          // Normalize message type to camelCase for switch
          const rawType = (data.message_type || data.type || '').toLowerCase();
          const type = rawType.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
          // Unified log entry builder
          const log = (msg: string, step: string = '', progress: number = 0) => ({
            timestamp: data.timestamp || new Date().toISOString(),
            step: step || '',
            message: msg || '',
            progress: progress || data.progress || 0
          });

          // Handle all backend message types
          switch (type) {
            case 'status':
            case 'statusUpdate':
              onUpdate(taskId, {
                status: data.status as JobState['status'],
                currentStep: data.current_step || data.step || 'Processing...',
                progress: Math.round((data.progress || 0) * 100)
              });
              if (onLogUpdate && (data.step || data.current_step)) {
                onLogUpdate(taskId, log(data.message || data.step || data.current_step || '', data.step || data.current_step || ''));
              }
              if (data.status === 'completed' && data.result) {
                if (!completedTasksRef.current.has(taskId)) {
                  completedTasksRef.current.add(taskId);
                  onCompletion(taskId, data.result || '', (data as any).hero_image_url || '');
                }
                eventSource.close();
              }
              if (data.status === 'failed' && data.error) {
                onError(taskId, data.error || '');
                eventSource.close();
              }
              break;
            case 'taskcreated':
              if (onLogUpdate) onLogUpdate(taskId, log('Task created and queued', 'Task Created'));
              break;
            case 'initializing':
              if (onLogUpdate) onLogUpdate(taskId, log(data.message || 'Initializing...', 'Initializing'));
              break;
            case 'agentthinking':
              if (onLogUpdate) onLogUpdate(taskId, log(
                `${data.agent_name ? data.agent_name + ': ' : ''}${data.thought || data.message || 'Agent is thinking...'}`,
                'Agent Thinking'
              ));
              break;
            case 'toolcall':
              if (onLogUpdate) onLogUpdate(taskId, log(
                `${data.agent_name ? data.agent_name + ' called ' : ''}${data.tool_name || 'a tool'}: ${data.input_summary || ''}`,
                'Tool Call'
              ));
              break;
            case 'toolresult':
              if (onLogUpdate) onLogUpdate(taskId, log(
                `${data.tool_name || 'Tool'} result: ${data.message || ''}`,
                'Tool Result'
              ));
              break;
            case 'contentstream':
              if (onLogUpdate) onLogUpdate(taskId, log(
                `${data.content_type || 'Content'}: ${data.content || ''}`,
                'Content Stream'
              ));
              break;
            case 'researchfinding':
              if (onLogUpdate) onLogUpdate(taskId, log(
                `Research finding: ${data.finding || data.message || ''}`,
                'Research Finding'
              ));
              break;
            case 'contentdraft':
              if (onLogUpdate) onLogUpdate(taskId, log(
                `Draft section: ${data.message || ''}`,
                'Content Draft'
              ));
              break;
            case 'factcheck':
              if (onLogUpdate) onLogUpdate(taskId, log(
                `Fact check: ${data.message || ''}`,
                'Fact Check'
              ));
              break;
            case 'revision':
              if (onLogUpdate) onLogUpdate(taskId, log(
                `Revision: ${data.message || ''}`,
                'Revision'
              ));
              break;
            case 'heroImage':
              if (onLogUpdate) onLogUpdate(taskId, log(
                `Hero image updated`,
                'Hero Image'
              ));
              break;
            case 'completed':
              if (onLogUpdate) onLogUpdate(taskId, log('Blog generation completed', 'Completed', 100));
              if (!completedTasksRef.current.has(taskId)) {
                completedTasksRef.current.add(taskId);
                onCompletion(taskId, data.result || '', (data as any).hero_image_url || '');
              }
              eventSource.close();
              break;
            case 'error':
              if (onLogUpdate) onLogUpdate(taskId, log(data.message || 'An error occurred', 'Error'));
              onError(taskId, data.message || 'An error occurred');
              eventSource.close();
              break;
            case 'logUpdate':
              if (onLogUpdate && data.step && data.message && data.timestamp) {
                onLogUpdate(data.task_id, {
                  timestamp: data.timestamp,
                  step: data.step,
                  message: data.message,
                  progress: data.progress || 0
                });
              }
              break;
            case 'streamEnded':
              eventSource.close();
              break;
            default:
              // Fallback: log unknown message types
              if (onLogUpdate) onLogUpdate(taskId, log(
                data.message || '[Unknown SSE message]',
                type || 'Unknown'
              ));
          }
        } catch (err) {
          console.error('Failed to parse SSE data:', err);
        }
      };

      eventSource.onerror = (err) => {
        console.error('❌ SSE connection error for task', taskId, ':', err);
        console.error('❌ EventSource readyState:', eventSource.readyState);
        console.error('❌ EventSource URL:', eventSource.url);
        
        // Try to provide more detailed error information
        const errorMsg = eventSource.readyState === EventSource.CLOSED 
          ? 'Connection was closed by server - check authentication or server logs'
          : 'Network connection failed - check internet connection and server availability';
        
        console.error('❌ Error type:', errorMsg);
        
        try { eventSource.close(); } catch {}
        if (eventSourceRef.current === eventSource) {
          eventSourceRef.current = null;
        }
        
        // Provide user-friendly error
        onError(taskId, 'Real-time connection failed. Your blog is still being generated in the background. Please refresh the page to check status.');
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
