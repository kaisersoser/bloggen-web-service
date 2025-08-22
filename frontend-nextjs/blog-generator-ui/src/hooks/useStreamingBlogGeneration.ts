import { useCallback, useRef } from 'react';
import { useEnhancedSSEConnection } from '@/hooks/useEnhancedSSE';
import { useStreamingContent } from './useStreamingContent';
import { JobState, LogEntry } from '../types/blog';

interface StreamingBlogGenerationProps {
  onJobUpdate: (taskId: string, updates: Partial<JobState>) => void;
  onJobCompletion: (taskId: string, content: string, heroImageUrl?: string) => void;
  onJobError: (taskId: string, error: string) => void;
  onJobLogUpdate?: (taskId: string, log: LogEntry) => void;
}

export const useStreamingBlogGeneration = ({
  onJobUpdate,
  onJobCompletion,
  onJobError,
  onJobLogUpdate
}: StreamingBlogGenerationProps) => {
  const { connectToTaskStream, closeConnection } = useEnhancedSSEConnection();
  const { 
    streamingContent, 
    handleContentStreamMessage, 
    handleProgressStreamMessage, 
    resetStreamingContent,
    getStreamingStats
  } = useStreamingContent();
  
  // Suppress unused variable warnings for planned streaming functionality
  void handleContentStreamMessage;
  void handleProgressStreamMessage;
  
  const currentTaskIdRef = useRef<string | null>(null);

  const startStreamingGeneration = useCallback(async (taskId: string) => {
    try {
      // Reset streaming state for new task
      resetStreamingContent();
      currentTaskIdRef.current = taskId;

      // SSE connection for task updates
      const connection = await connectToTaskStream(
        taskId,
        // Standard job updates
        onJobUpdate,
        onJobCompletion,
        onJobError,
        onJobLogUpdate
      );

      return connection;
    } catch (error) {
      console.error('Failed to start streaming generation:', error);
      onJobError(taskId, `Failed to start streaming: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return null;
    }
  }, [
    connectToTaskStream,
    onJobUpdate,
    onJobCompletion,
    onJobError,
    onJobLogUpdate,
    resetStreamingContent
  ]);

  const stopStreaming = useCallback(() => {
    closeConnection();
    currentTaskIdRef.current = null;
  }, [closeConnection]);

  // SSE doesn't have isConnected state like WebSocket, so we track it manually
  const isConnected = currentTaskIdRef.current !== null;

  return {
    // Streaming connection management
    startStreamingGeneration,
    stopStreaming,
    isConnected,
    
    // Real-time streaming content
    streamingContent,
    streamingStats: getStreamingStats(),
    
    // Current task tracking
    currentTaskId: currentTaskIdRef.current
  };
};
