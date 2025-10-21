/**
 * useWorkflowSSE Hook
 * 
 * Connects SSE events from the blog generation process to the WorkflowGraph component.
 * Transforms SSE events into graph updates for real-time visualization.
 * 
 * This hook reuses the existing SSE infrastructure but provides a specialized
 * callback interface for the workflow graph builder.
 */

import { useEffect, useRef } from 'react';
import { useSession } from 'next-auth/react';
import { API_BASE_URL } from '@/config/constants';
import { logger } from '@/lib/logger';
import { authTokenManager } from '@/lib/authTokenManager';
import type { SSEEvent } from '@/types/workflow-graph';

interface UseWorkflowSSEOptions {
  taskId: string | null;
  onEvent?: (event: SSEEvent) => void;
  enabled?: boolean;
}

/**
 * Transform backend SSE event to WorkflowGraph SSEEvent format
 */
function transformSSEEvent(rawData: any): SSEEvent | null {
  if (!rawData) {
    console.warn('🔶 [transformSSEEvent] Received null/undefined rawData');
    return null;
  }

  console.log('🔍 [transformSSEEvent] Input rawData:', JSON.stringify(rawData, null, 2));

  // Determine event type based on message_type or type field
  const messageType = rawData.message_type || rawData.type;
  console.log('🏷️ [transformSSEEvent] Message type detected:', messageType);
  
  let eventType: SSEEvent['type'];
  
  switch (messageType) {
    case 'status':
    case 'taskcreated':
    case 'initializing':
      eventType = 'status';
      break;
    case 'agentthinking':
      eventType = 'agent_thinking';
      break;
    case 'toolcall':
      eventType = 'tool_usage';
      break;
    case 'contentstream':
      eventType = 'content_stream';
      break;
    case 'error':
      eventType = 'error';
      break;
    default:
      console.log('📝 [transformSSEEvent] Unknown message type, defaulting to "log"');
      eventType = 'log';
  }
  
  console.log('🎯 [transformSSEEvent] Mapped to event type:', eventType);

  return {
    type: eventType,
    data: {
      task_id: rawData.task_id || '',
      status: rawData.status || rawData.current_step || '',
      message: rawData.message || '',
      step: rawData.step || rawData.current_step,
      progress: rawData.progress,
      timestamp: rawData.timestamp || new Date().toISOString(),
      
      // Agent thinking fields
      agent_name: rawData.agent_name,
      reasoning: rawData.thought || rawData.reasoning,
      
      // Tool usage fields
      tool_name: rawData.tool_name,
      tool_status: rawData.tool_status,
      tool_output: rawData.tool_output,
      tool_error: rawData.tool_error,
      
      // Content stream fields
      content: rawData.content,
      draft_version: rawData.draft_version,
      
      // Error fields
      error: rawData.error,
      error_type: rawData.error_type,
    }
  };
}

/**
 * Hook to establish SSE connection for workflow visualization
 */
export function useWorkflowSSE({ taskId, onEvent, enabled = true }: UseWorkflowSSEOptions) {
  const { data: session, status } = useSession();
  const eventSourceRef = useRef<EventSource | null>(null);
  const isConnectingRef = useRef(false);

  useEffect(() => {
    // Don't connect if disabled or no taskId
    if (!enabled || !taskId || status !== 'authenticated' || !session) {
      return;
    }

    // Prevent duplicate connections
    if (isConnectingRef.current || eventSourceRef.current) {
      return;
    }

    const connectToSSE = async () => {
      try {
        isConnectingRef.current = true;

        // Get auth token
        const token = await authTokenManager.getToken();
        if (!token) {
          logger.error('[useWorkflowSSE] No auth token available');
          return;
        }

        // Construct SSE URL with token (EventSource doesn't support headers)
        const sseUrl = `${API_BASE_URL}/stream/${taskId}?token=${encodeURIComponent(token)}`;
        
        logger.info('[useWorkflowSSE] Connecting to workflow stream', { taskId });
        
        const eventSource = new EventSource(sseUrl);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          logger.info('[useWorkflowSSE] Connection established', { taskId });
          console.log('🟢 [useWorkflowSSE] SSE Connection OPEN for taskId:', taskId);
        };

        eventSource.onmessage = (event) => {
          try {
            console.log('📨 [useWorkflowSSE] RAW SSE EVENT:', event.data);
            const rawData = JSON.parse(event.data);
            console.log('📦 [useWorkflowSSE] PARSED DATA:', rawData);
            
            const transformedEvent = transformSSEEvent(rawData);
            console.log('🔄 [useWorkflowSSE] TRANSFORMED EVENT:', transformedEvent);
            
            if (transformedEvent && onEvent) {
              console.log('✅ [useWorkflowSSE] Calling onEvent callback with:', transformedEvent.type);
              onEvent(transformedEvent);
            } else {
              console.warn('⚠️ [useWorkflowSSE] No transformed event or callback missing', { 
                hasTransformedEvent: !!transformedEvent, 
                hasCallback: !!onEvent 
              });
            }
          } catch (error) {
            logger.error('[useWorkflowSSE] Failed to parse SSE message', error);
            console.error('❌ [useWorkflowSSE] PARSE ERROR:', error, 'Raw data:', event.data);
          }
        };

        eventSource.onerror = (error) => {
          logger.error('[useWorkflowSSE] SSE error', error);
          
          // Close and cleanup on error
          if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
          }
          isConnectingRef.current = false;
        };

      } catch (error) {
        logger.error('[useWorkflowSSE] Connection failed', error);
        isConnectingRef.current = false;
      }
    };

    connectToSSE();

    // Cleanup on unmount or taskId change
    return () => {
      if (eventSourceRef.current) {
        logger.info('[useWorkflowSSE] Closing connection', { taskId });
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      isConnectingRef.current = false;
    };
  }, [taskId, enabled, session, status, onEvent]);

  return {
    isConnected: eventSourceRef.current?.readyState === EventSource.OPEN,
  };
}
