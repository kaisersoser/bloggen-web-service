import { useRef, useCallback, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { API_BASE_URL } from '@/config/constants';
import { logger } from '@/lib/logger';
import { VERBOSE_LOGGING_ENABLED } from '@/lib/logger/env';
import { JobState, SSEUpdate, LogEntry } from '@/types/blog';
import { TimeoutResistantSSE } from '@/lib/TimeoutResistantSSE';
import { authTokenManager, AuthTokenError } from '@/lib/authTokenManager';

export interface ConnectionStateChange {
  status: 'connecting' | 'connected' | 'reconnecting' | 'offline_wait' | 'closed' | 'error';
  message: string;
  attempt?: number;
  delayMs?: number;
  timestamp: string;
}

export function useEnhancedSSEConnection() {
  const { data: session, status } = useSession();
  const sseConnectionRef = useRef<TimeoutResistantSSE | null>(null);
  const completedTasksRef = useRef<Set<string>>(new Set());
  const contentCacheRef = useRef<Map<string, string>>(new Map());

  // Helper function to send completion acknowledgment to backend
  const sendCompletionAcknowledgment = useCallback(async (taskId: string) => {
    try {
      const canLogVerbose = VERBOSE_LOGGING_ENABLED && logger.shouldLog('info');
      if (status !== 'authenticated' || !session) {
        throw new Error('Please sign in to send acknowledgment');
      }

      let token: string | null = null;
      try {
        token = await authTokenManager.getToken();
      } catch (error) {
        if (error instanceof AuthTokenError && error.status === 401) {
          throw new Error('Authentication required to send acknowledgment');
        }
        throw error;
      }

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
      if (canLogVerbose) {
        logger.info('✅ Completion acknowledgment sent', result);
      }
      return result;
      
    } catch (error) {
      logger.error('❌ Failed to send completion acknowledgment', error);
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
    const canLogVerbose = VERBOSE_LOGGING_ENABLED && logger.shouldLog('info');
    if (canLogVerbose) {
      logger.info('📨 Processing SSE message', { timestamp: new Date().toISOString(), messageType: data.message_type || data.type });
    }

    // Handle enhanced message types from Phase 1 Foundation
    if (data.message_type) {
      switch (data.message_type) {
        case 'status':
          if (canLogVerbose) {
            logger.info('🔢 Frontend: Received status update', { progress: data.progress, taskId });
            logger.info('🔢 Frontend: Message content', { message: data.message, step: data.step, taskId });
          }
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
          if (canLogVerbose) {
            logger.info('🎉 Direct completion message received', { taskId });
          }
          if (!completedTasksRef.current.has(taskId)) {
            completedTasksRef.current.add(taskId);
            const cachedContent = contentCacheRef.current.get(taskId);
            const finalContent = data.final_content || data.content || cachedContent || '';
            const heroImageUrl = data.hero_image_url;
            onCompletion(taskId, finalContent, heroImageUrl);
            contentCacheRef.current.delete(taskId);
            
            // Send acknowledgment to backend for 2-phase completion protocol
            try {
              await sendCompletionAcknowledgment(taskId);
              if (canLogVerbose) {
                logger.info('✅ Completion acknowledgment sent to backend for task', { taskId });
              }
            } catch (error) {
              logger.warn('⚠️ Failed to send completion acknowledgment', error);
            }
          }
          break;
        case 'completion_pending':
          // Handle 2-phase completion protocol
          if (canLogVerbose) {
            logger.info('⏳ Completion pending message received', { taskId });
          }
          if (!completedTasksRef.current.has(taskId)) {
            completedTasksRef.current.add(taskId);
            const cachedContent = contentCacheRef.current.get(taskId);
            const finalContent = data.final_content || data.content || cachedContent || '';
            const heroImageUrl = data.hero_image_url;
            onCompletion(taskId, finalContent, heroImageUrl);
            contentCacheRef.current.delete(taskId);
            
            // Send acknowledgment to backend for 2-phase completion protocol
            try {
              await sendCompletionAcknowledgment(taskId);
              if (canLogVerbose) {
                logger.info('✅ Completion acknowledgment sent to backend for task', { taskId });
              }
            } catch (error) {
              logger.warn('⚠️ Failed to send completion acknowledgment', error);
            }
          }
          break;
        case 'keepalive':
        case 'connected':
          if (canLogVerbose) {
            logger.info('💓 Keepalive/connection message received', { taskId });
          }
          break;
        default:
          if (canLogVerbose) {
            logger.info('❓ Unknown message type encountered', { messageType: data.message_type, data });
          }
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
      
      if (canLogVerbose) {
        logger.info('📝 Processing fallback message', { messageType, messageContent });
      }
      
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
      if (data.status === 'completed') {
        if (!completedTasksRef.current.has(taskId)) {
          completedTasksRef.current.add(taskId);
          const cachedContent = contentCacheRef.current.get(taskId);
          const finalContent = data.result || cachedContent || '';
          onCompletion(taskId, finalContent, (data as any).hero_image_url);
          contentCacheRef.current.delete(taskId);
          // Close the SSE connection when task completes
          if (sseConnectionRef.current) {
            if (canLogVerbose) {
              logger.info('✅ Legacy task completed - closing SSE connection', { taskId });
            }
            sseConnectionRef.current.close();
            sseConnectionRef.current = null;
            
            // Add "Connection closed" message to console
            if (onLogUpdate) {
              const connectionClosedMessage = {
                timestamp: new Date().toISOString(),
                step: 'connection',
                message: 'Connection closed',
                progress: 100
              };
              onLogUpdate(taskId, connectionClosedMessage);
            }
          }
        }
      }
      if (data.status === 'failed' && data.error) {
        onError(taskId, data.error);
        contentCacheRef.current.delete(taskId);
        // Close the SSE connection on error
        if (sseConnectionRef.current) {
          logger.warn('❌ Legacy task failed - closing SSE connection', { taskId });
          sseConnectionRef.current.close();
          sseConnectionRef.current = null;
          
          // Add "Connection closed" message to console
          if (onLogUpdate) {
            const connectionClosedMessage = {
              timestamp: new Date().toISOString(),
              step: 'connection',
              message: 'Connection closed',
              progress: 100
            };
            onLogUpdate(taskId, connectionClosedMessage);
          }
        }
      }
      return;
    }

    // Structured type field format
    switch (data.type) {
      case 'connected':
        if (canLogVerbose) {
          logger.info('✅ SSE connection confirmed', { taskId });
        }
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
        if (canLogVerbose) {
          logger.info('🔚 Stream ended for task', { taskId });
        }
        break;
      case 'error':
        logger.error('❌ Stream error', { message: data.message, taskId });
        // Call the onError callback to properly handle the error in the UI
        onError(taskId, data.error || data.message || 'Unknown error occurred');
        contentCacheRef.current.delete(taskId);
        break;
    }
  }, [sendCompletionAcknowledgment, contentCacheRef]);

  const connectToTaskStream = useCallback(async (
    taskId: string,
    onUpdate: (taskId: string, updates: Partial<JobState>) => void,
    onCompletion: (taskId: string, content: string, heroImageUrl?: string) => void,
    onError: (taskId: string, error: string) => void,
    onLogUpdate?: (taskId: string, log: LogEntry) => void,
    onConnectionStateChange?: (taskId: string, state: ConnectionStateChange) => void
  ): Promise<TimeoutResistantSSE> => {
    try {
      const canLogVerbose = VERBOSE_LOGGING_ENABLED && logger.shouldLog('info');

      if (status !== 'authenticated' || !session) {
        throw new Error('Please sign in to connect to the stream');
      }

      if (sseConnectionRef.current) {
        sseConnectionRef.current.close();
        sseConnectionRef.current = null;
      }

      contentCacheRef.current.delete(taskId);

      const getAuthToken = async (forceRefresh = false): Promise<string> => {
        let token: string | null = null;
        try {
          token = await authTokenManager.getToken({ forceRefresh });
        } catch (error) {
          if (error instanceof AuthTokenError && error.status === 401) {
            throw new Error('Session expired - please sign out and sign back in');
          }
          if (error instanceof Error) {
            throw error;
          }
          throw new Error('Failed to get authentication token');
        }

        if (!token) {
          throw new Error('No authentication token received');
        }

        return token;
      };

      const streamUrlFactory = async () => {
        const token = await getAuthToken();
        const streamUrl = `${API_BASE_URL}/stream/${taskId}?token=${encodeURIComponent(token)}`;
        if (canLogVerbose) {
          logger.info('🔗 Prepared Enhanced SSE URL', {
            taskId,
            tokenLength: token.length,
          });
        }
        return streamUrl;
      };

      // Prime token acquisition so auth errors surface immediately
  await getAuthToken();

      const sseOptions = {
        timeout: 600000,
        retryDelay: 2500,
        maxRetries: 8,
        reconnectOnError: true,
        maxRetryDelay: 45000,
        backoffMultiplier: 1.8,
        jitterMs: 750,
      } as const;

      const sseConnection = new TimeoutResistantSSE(streamUrlFactory, sseOptions);

      onConnectionStateChange?.(taskId, {
        status: 'connecting',
        message: 'Connecting to live updates…',
        timestamp: new Date().toISOString(),
      });

      sseConnectionRef.current = sseConnection;

      sseConnection.addEventListener('open', () => {
        if (canLogVerbose) {
          logger.info('✅ Enhanced SSE connection established', { taskId, timestamp: new Date().toISOString() });
        }
        if (onLogUpdate) {
          onLogUpdate(taskId, {
            timestamp: new Date().toISOString(),
            step: 'connection',
            message: 'Live updates connected',
            progress: 5,
          });
        }
        onConnectionStateChange?.(taskId, {
          status: 'connected',
          message: 'Live updates connected',
          timestamp: new Date().toISOString(),
        });
      });

      sseConnection.addEventListener('reconnecting', ({ attempt, delay }) => {
        if (canLogVerbose) {
          logger.warn('♻️ Enhanced SSE reconnect scheduled', { taskId, attempt, delay });
        }
        onUpdate(taskId, {
          currentStep: 'Reconnecting to live updates…',
        });
        if (onLogUpdate) {
          onLogUpdate(taskId, {
            timestamp: new Date().toISOString(),
            step: 'connection',
            message: `Reconnecting in ${(delay / 1000).toFixed(1)}s (attempt ${attempt})`,
            progress: 0,
          });
        }
        onConnectionStateChange?.(taskId, {
          status: 'reconnecting',
          message: `Reconnecting in ${(delay / 1000).toFixed(1)} seconds…`,
          attempt,
          delayMs: delay,
          timestamp: new Date().toISOString(),
        });
      });

      sseConnection.addEventListener('offline_wait', ({ attempt }) => {
        if (canLogVerbose) {
          logger.info('📴 Browser offline detected, waiting to reconnect', { taskId, attempt });
        }
        onUpdate(taskId, {
          currentStep: 'Waiting for network connectivity…',
        });
        if (onLogUpdate) {
          onLogUpdate(taskId, {
            timestamp: new Date().toISOString(),
            step: 'connection',
            message: 'Offline detected. Waiting for connection before retrying…',
            progress: 0,
          });
        }
        onConnectionStateChange?.(taskId, {
          status: 'offline_wait',
          message: 'Offline detected. Waiting for network before retrying…',
          attempt,
          timestamp: new Date().toISOString(),
        });
      });

      sseConnection.addEventListener('reconnected', ({ attempt }) => {
        if (canLogVerbose) {
          logger.info('🔄 Enhanced SSE reconnected', { taskId, attempt });
        }
        onUpdate(taskId, {
          currentStep: 'Connection restored. Resuming updates…',
        });
        if (onLogUpdate) {
          onLogUpdate(taskId, {
            timestamp: new Date().toISOString(),
            step: 'connection',
            message: `Connection restored (attempt ${attempt})`,
            progress: 10,
          });
        }
        onConnectionStateChange?.(taskId, {
          status: 'connected',
          message: `Connection restored (attempt ${attempt})`,
          attempt,
          timestamp: new Date().toISOString(),
        });
      });

      sseConnection.addEventListener('error', (error: any) => {
        const isConnectionFailure = typeof error?.retryCount === 'number' || Boolean(error?.originalError);

        if (!isConnectionFailure) {
          // Server-sent error events are routed through processSSEMessage to avoid double notifications
          return;
        }

        logger.error('❌ Enhanced SSE connection error', { taskId, timestamp: new Date().toISOString(), error });
        contentCacheRef.current.delete(taskId);
        onError(taskId, error.message || 'Connection failed. Your blog generation continues in the background.');
        onConnectionStateChange?.(taskId, {
          status: 'error',
          message: error.message || 'Connection failed. Live updates will retry automatically.',
          timestamp: new Date().toISOString(),
        });
      });

      sseConnection.addEventListener('close', (data) => {
        contentCacheRef.current.delete(taskId);
        if (canLogVerbose) {
          logger.info('🔌 Enhanced SSE connection closed', { taskId, timestamp: new Date().toISOString(), reason: data?.reason });
        }
        if (onLogUpdate) {
          onLogUpdate(taskId, {
            timestamp: new Date().toISOString(),
            step: 'connection',
            message: 'Connection closed',
            progress: 100,
          });
        }
        onConnectionStateChange?.(taskId, {
          status: 'closed',
          message: data?.reason ? `Connection closed: ${data.reason}` : 'Connection closed',
          timestamp: new Date().toISOString(),
        });
      });

      sseConnection.addEventListener('message', async (data) => {
        await processSSEMessage(data, taskId, onUpdate, onCompletion, onError, onLogUpdate);
      });

      const messageTypes = [
        'status',
        'taskcreated',
        'initializing',
        'agentthinking',
        'toolcall',
        'contentstream',
        'researchfinding',
        'completed',
        'completion_pending',
        'error',
        'keepalive',
        'connected',
        'log_update',
        'status_update',
        'stream_ended',
      ];

      messageTypes.forEach((type) => {
        sseConnection.addEventListener(type, async (data) => {
          await processSSEMessage({ ...data, message_type: type }, taskId, onUpdate, onCompletion, onError, onLogUpdate);
        });
      });

      sseConnection.addEventListener('content_progress', (data) => {
        const totalBytes = typeof data.total === 'number' ? data.total : 0;
        const receivedBytes = typeof data.received === 'number' ? data.received : 0;
        const progressValue = typeof data.progress === 'number' && Number.isFinite(data.progress)
          ? data.progress
          : totalBytes > 0
            ? (receivedBytes / totalBytes) * 100
            : 0;
        const clampedProgress = Math.min(100, Math.max(0, progressValue));

        if (onLogUpdate) {
          const progressMessage = totalBytes > 0
            ? `📡 Receiving content… ${clampedProgress.toFixed(1)}% (${receivedBytes}/${totalBytes} bytes)`
            : `📡 Receiving streaming content… ${receivedBytes} bytes`;

          onLogUpdate(taskId, {
            timestamp: new Date().toISOString(),
            step: 'Content Streaming',
            message: progressMessage,
            progress: clampedProgress,
          });
        }
      });

      sseConnection.addEventListener('content_complete', (data) => {
        contentCacheRef.current.set(taskId, data.content);
        if (canLogVerbose) {
          logger.info('📄 Large content buffer assembled', {
            taskId,
            contentLength: data.content?.length ?? 0,
          });
        }
        onUpdate(taskId, {
          currentStep: 'Finalizing blog content…',
        });
        if (onLogUpdate) {
          onLogUpdate(taskId, {
            timestamp: new Date().toISOString(),
            step: 'Content Streaming',
            message: 'Full content received. Waiting for finalization…',
            progress: 95,
          });
        }
      });

      await sseConnection.connect();

      return sseConnection;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create Enhanced SSE connection';
      onConnectionStateChange?.(taskId, {
        status: 'error',
        message: errorMessage,
        timestamp: new Date().toISOString(),
      });
      logger.error('Failed to create Enhanced SSE connection', err);
      throw err;
    }
  }, [session, status, processSSEMessage, contentCacheRef]);

  const closeConnection = useCallback(() => {
    if (sseConnectionRef.current) {
      sseConnectionRef.current.close();
      sseConnectionRef.current = null;
    }
    contentCacheRef.current.clear();
  }, []);

  useEffect(() => () => closeConnection(), [closeConnection]);

  return { 
    connectToTaskStream, 
    closeConnection, 
    sseConnectionRef, 
    completedTasksRef 
  };
}
