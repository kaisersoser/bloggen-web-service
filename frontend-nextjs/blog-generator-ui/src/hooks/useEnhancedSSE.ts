import { useRef, useCallback, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { API_BASE_URL } from '@/config/constants';
import { JobState, SSEUpdate, LogEntry } from '@/types/blog';
import { TimeoutResistantSSE } from '@/lib/TimeoutResistantSSE';

export function useEnhancedSSEConnection() {
  const { data: session, status } = useSession();
  const sseConnectionRef = useRef<TimeoutResistantSSE | null>(null);
  const completedTasksRef = useRef<Set<string>>(new Set());

  // Helper function to send completion acknowledgment to backend
  const sendCompletionAcknowledgment = useCallback(async (taskId: string) => {
    try {
      if (status !== 'authenticated' || !session) {
        throw new Error('Please sign in to send acknowledgment');
      }

      // Get fresh JWT token for authentication
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

      const response = await fetch(`${API_BASE_URL}/tasks/${taskId}/acknowledge-completion`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('✅ Completion acknowledgment sent:', result);
      return result;
      
    } catch (error) {
      console.error('❌ Failed to send completion acknowledgment:', error);
      throw error;
    }
  }, [session, status]);

  // Helper function to process SSE messages
  const processSSEMessage = useCallback(async (
    data: SSEUpdate,
    taskId: string,
    onUpdate: (taskId: string, updates: Partial<JobState>) => void,
    onCompletion: (taskId: string, content: string, heroImageUrl?: string) => void,
    onError: (taskId: string, error: string) => void,
    onLogUpdate?: (taskId: string, log: LogEntry) => void
  ) => {
    console.log('📨 Processing SSE message at', new Date().toISOString(), ':', data.message_type || data.type);

    // Handle enhanced message types from Phase 1 Foundation
    if (data.message_type) {
      switch (data.message_type) {
        case 'status':
          console.log('🔢 Frontend: Received status update with progress:', data.progress, 'for task:', taskId);
          console.log('🔢 Frontend: Message content:', data.message, 'Step:', data.step);
          onUpdate(taskId, {
            status: data.status as JobState['status'],
            currentStep: data.message || data.step,
            progress: data.progress || 0
          });
          if (onLogUpdate) {
            onLogUpdate(taskId, {
              timestamp: data.timestamp || new Date().toISOString(),
              step: data.step || 'Processing',
              message: data.message || 'Processing...',
              progress: data.progress || 0
            });
          }
          break;
        case 'taskcreated':
          onUpdate(taskId, {
            status: 'queued' as JobState['status'],
            currentStep: data.message,
            progress: 0
          });
          break;
        case 'initializing':
          onUpdate(taskId, {
            status: 'in_progress' as JobState['status'],
            currentStep: data.message,
            progress: data.progress || 0
          });
          break;
        case 'agentthinking':
          if (onLogUpdate) {
            onLogUpdate(taskId, {
              timestamp: data.timestamp || new Date().toISOString(),
              step: `Agent: ${data.agent_name || 'Unknown'}`,
              message: `💭 ${data.thought || 'Thinking...'}`,
              progress: 0
            });
          }
          break;
        case 'toolcall':
          if (onLogUpdate) {
            onLogUpdate(taskId, {
              timestamp: data.timestamp || new Date().toISOString(),
              step: `Tool: ${data.tool_name || 'Unknown'}`,
              message: `🔧 ${data.input_summary || 'Using tool...'}`,
              progress: 0
            });
          }
          break;
        case 'contentstream':
          if (onLogUpdate) {
            onLogUpdate(taskId, {
              timestamp: data.timestamp || new Date().toISOString(),
              step: `Content: ${data.content_type || 'Unknown'}`,
              message: `📄 Generating ${data.content_type || 'content'} (${data.word_count || 0} words)`,
              progress: 0
            });
          }
          break;
        case 'researchfinding':
          if (onLogUpdate) {
            onLogUpdate(taskId, {
              timestamp: data.timestamp || new Date().toISOString(),
              step: 'Research Finding',
              message: `🔍 ${data.finding || 'Research finding...'}`,
              progress: 0
            });
          }
          break;
        case 'completed':
          // Handle direct completion messages (new format)
          console.log('🎉 Direct completion message received for task', taskId);
          if (!completedTasksRef.current.has(taskId)) {
            completedTasksRef.current.add(taskId);
            const finalContent = data.final_content || data.content || '';
            const heroImageUrl = data.hero_image_url;
            onCompletion(taskId, finalContent, heroImageUrl);
            
            // Send acknowledgment to backend for 2-phase completion protocol
            try {
              await sendCompletionAcknowledgment(taskId);
              console.log('✅ Completion acknowledgment sent to backend for task', taskId);
            } catch (error) {
              console.warn('⚠️ Failed to send completion acknowledgment:', error);
            }
          }
          break;
        case 'completion_pending':
          // Handle 2-phase completion protocol
          console.log('⏳ Completion pending message received for task', taskId);
          if (!completedTasksRef.current.has(taskId)) {
            completedTasksRef.current.add(taskId);
            const finalContent = data.final_content || data.content || '';
            const heroImageUrl = data.hero_image_url;
            onCompletion(taskId, finalContent, heroImageUrl);
            
            // Send acknowledgment to backend for 2-phase completion protocol
            try {
              await sendCompletionAcknowledgment(taskId);
              console.log('✅ Completion acknowledgment sent to backend for task', taskId);
            } catch (error) {
              console.warn('⚠️ Failed to send completion acknowledgment:', error);
            }
          }
          break;
        case 'keepalive':
        case 'connected':
          console.log('💓 Keepalive/connection message received for task', taskId);
          break;
        default:
          console.log('❓ Unknown message type:', data.message_type, data);
          // Fallback: treat unknown messages as general log entries
          if (onLogUpdate && data.message) {
            onLogUpdate(taskId, {
              timestamp: data.timestamp || new Date().toISOString(),
              step: data.message_type || 'Unknown',
              message: data.message,
              progress: data.progress || 0
            });
          }
          break;
      }
      return;
    }

    // Enhanced fallback for any message with content (with proper type handling)
    const anyData = data as any;
    if (data.message || anyData.data) {
      const messageContent = data.message || (typeof anyData.data === 'string' ? anyData.data : JSON.stringify(anyData.data));
      const messageType = anyData.type || anyData.event || 'message';
      
      console.log('📝 Processing fallback message:', messageType, messageContent);
      
      if (onLogUpdate) {
        onLogUpdate(taskId, {
          timestamp: data.timestamp || new Date().toISOString(),
          step: messageType,
          message: messageContent,
          progress: data.progress || 0
        });
      }
    }

    // Legacy format (status + step) - keep for backward compatibility
    if (data.status && data.step && data.timestamp) {
      onUpdate(taskId, {
        status: data.status as JobState['status'],
        currentStep: data.step,
        progress: data.progress !== undefined ? data.progress : 0  // Use actual progress or 0, not default 50
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
          // Close the SSE connection when task completes
          if (sseConnectionRef.current) {
            console.log('✅ Legacy task completed - closing SSE connection');
            sseConnectionRef.current.close();
            sseConnectionRef.current = null;
          }
        }
      }
      if (data.status === 'failed' && data.error) {
        onError(taskId, data.error);
        // Close the SSE connection on error
        if (sseConnectionRef.current) {
          console.log('❌ Legacy task failed - closing SSE connection');
          sseConnectionRef.current.close();
          sseConnectionRef.current = null;
        }
      }
      return;
    }

    // Structured type field format
    switch (data.type) {
      case 'connected':
        console.log('✅ SSE connection confirmed for task', taskId);
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
        }
        if (data.status === 'failed' && data.error) {
          onError(data.task_id, data.error);
        }
        break;
      case 'stream_ended':
        console.log('🔚 Stream ended for task', taskId);
        break;
      case 'error':
        console.error('❌ Stream error:', data.message);
        // Call the onError callback to properly handle the error in the UI
        onError(taskId, data.error || data.message || 'Unknown error occurred');
        break;
    }
  }, [sendCompletionAcknowledgment]);

  const connectToTaskStream = useCallback(async (
    taskId: string,
    onUpdate: (taskId: string, updates: Partial<JobState>) => void,
    onCompletion: (taskId: string, content: string, heroImageUrl?: string) => void,
    onError: (taskId: string, error: string) => void,
    onLogUpdate?: (taskId: string, log: LogEntry) => void
  ): Promise<TimeoutResistantSSE> => {
    try {
      // Check authentication first
      if (status !== 'authenticated' || !session) {
        throw new Error('Please sign in to connect to the stream');
      }

      // Close any existing connection first
      if (sseConnectionRef.current) {
        sseConnectionRef.current.close();
        sseConnectionRef.current = null;
      }

      // Get fresh JWT token
      const tokenResponse = await fetch('/api/auth/jwt-token', {
        method: 'GET',
        credentials: 'include'
      });
      
      if (!tokenResponse.ok) {
        if (tokenResponse.status === 401) {
          throw new Error('Session expired - please sign out and sign back in');
        }
        throw new Error(`Authentication failed: ${tokenResponse.status}`);
      }
      
      const { token } = await tokenResponse.json();
      if (!token) {
        throw new Error('No authentication token received');
      }

      const streamUrl = `${API_BASE_URL}/stream/${taskId}?token=${encodeURIComponent(token)}`;
      
      console.log('🔗 Starting Enhanced SSE connection to:', streamUrl);
      console.log('🔗 Task ID:', taskId);
      
      // Create enhanced SSE connection with proper timeout strategy
      const sseConnection = new TimeoutResistantSSE(streamUrl, {
        timeout: 600000, // Increase to 10 minutes for blog generation + acknowledgment protocol
        retryDelay: 3000, // Reduced to 3 seconds for faster recovery
        maxRetries: 5, // Increased retries for better reliability
        reconnectOnError: true
      });

      sseConnectionRef.current = sseConnection;

      // Set up event listeners
      sseConnection.addEventListener('open', () => {
        console.log('✅ Enhanced SSE connection established for task', taskId, 'at', new Date().toISOString());
      });

      sseConnection.addEventListener('error', (error) => {
        console.error('❌ Enhanced SSE connection error for task', taskId, 'at', new Date().toISOString(), ':', error);
        onError(taskId, error.message || 'Connection failed. Your blog generation continues in the background.');
      });

      sseConnection.addEventListener('close', (data) => {
        console.log('🔌 Enhanced SSE connection closed for task', taskId, 'at', new Date().toISOString(), ':', data.reason);
      });

      // Handle regular messages
      sseConnection.addEventListener('message', async (data) => {
        await processSSEMessage(data, taskId, onUpdate, onCompletion, onError, onLogUpdate);
      });

      // Handle all other message types
      const messageTypes = [
        'status', 'taskcreated', 'initializing', 'agentthinking', 'toolcall',
        'contentstream', 'researchfinding', 'completed', 'completion_pending', 'error', 'keepalive',
        'connected', 'log_update', 'status_update', 'stream_ended'
      ];

      messageTypes.forEach(type => {
        sseConnection.addEventListener(type, async (data) => {
          await processSSEMessage({ ...data, message_type: type }, taskId, onUpdate, onCompletion, onError, onLogUpdate);
        });
      });

      // Handle chunked content for large AI data
      sseConnection.addEventListener('content_progress', (data) => {
        if (onLogUpdate) {
          onLogUpdate(taskId, {
            timestamp: new Date().toISOString(),
            step: 'Content Streaming',
            message: `📡 Receiving content... ${data.progress.toFixed(1)}% (${data.received}/${data.total} bytes)`,
            progress: data.progress
          });
        }
      });

      sseConnection.addEventListener('content_complete', (data) => {
        console.log('📄 Large content received for task', taskId);
        if (!completedTasksRef.current.has(taskId)) {
          completedTasksRef.current.add(taskId);
          onCompletion(taskId, data.content);
          // Close the SSE connection when large content completes
          console.log('✅ Large content completed - closing SSE connection');
          sseConnection.close();
          sseConnectionRef.current = null;
        }
      });

      // Start the connection
      await sseConnection.connect();

      return sseConnection;

    } catch (err) {
      console.error('Failed to create Enhanced SSE connection:', err);
      throw err;
    }
  }, [session, status, processSSEMessage]);

  const closeConnection = useCallback(() => {
    if (sseConnectionRef.current) {
      sseConnectionRef.current.close();
      sseConnectionRef.current = null;
    }
  }, []);

  useEffect(() => () => closeConnection(), [closeConnection]);

  return { 
    connectToTaskStream, 
    closeConnection, 
    sseConnectionRef, 
    completedTasksRef 
  };
}
