import { useCallback, useEffect, useRef } from 'react';
import { logger } from '@/lib/logger';
import { blogService } from '@/lib/services/blog';
import { taskService } from '@/lib/services/task';
import { useEnhancedSSEConnection, type ConnectionStateChange } from '@/hooks/useEnhancedSSE';
import { useAuthenticationErrorHandler } from '@/hooks/useAuthenticationErrorHandler';
import type { BlogData, ErrorInfo, JobState, LogEntry } from '@/types/blog';
import type { GenerationState, GenerationStateActions } from '@/hooks/useGenerationStateManager';

interface UseGenerationLifecycleParams {
  state: GenerationState;
  actions: GenerationStateActions;
  canGenerate: boolean;
  jobs: JobState[];
  previousBlogs: BlogData[];
  updateJob: (taskId: string, updates: Partial<JobState>) => void;
  createJob: (taskId: string, topic: string, instructions: string) => void;
  deleteJob: (taskId: string) => void;
  refetchStats: () => Promise<unknown>;
  fetchPreviousBlogs: () => Promise<unknown>;
  addTemporaryJob: (job: JobState) => void;
  isAuthenticated: boolean;
  isAuthLoading: boolean;
}

interface UseGenerationLifecycleReturn {
  handleGenerateBlog: (topic: string, instructions: string) => Promise<void>;
  closeActiveConnection: () => void;
}

export function useGenerationLifecycle({
  state,
  actions,
  canGenerate,
  jobs,
  previousBlogs,
  updateJob,
  createJob,
  deleteJob,
  refetchStats,
  fetchPreviousBlogs,
  addTemporaryJob,
  isAuthenticated,
  isAuthLoading,
}: UseGenerationLifecycleParams): UseGenerationLifecycleReturn {
  const { handleAuthError } = useAuthenticationErrorHandler();
  const { connectToTaskStream, closeConnection, completedTasksRef } = useEnhancedSSEConnection();
  const firstUpdateReceivedRef = useRef<string | null>(null);
  const isRecoveringRef = useRef(false);

  const handleConnectionStateChange = useCallback((taskId: string, state: ConnectionStateChange) => {
    updateJob(taskId, {
      connectionState: state.status,
      connectionMessage: state.message,
      connectionUpdatedAt: state.timestamp,
    });
  }, [updateJob]);

  const resetActiveConnection = useCallback(() => {
    actions.setActiveConnectionId(null);
    actions.setIsGenerating(false);
  }, [actions]);

  const handleTaskCompletion = useCallback(async (taskId: string, content: string, heroImageUrl?: string) => {
    if (logger.shouldLog('debug')) {
      logger.debug('handleTaskCompletion', {
        taskId,
        contentLength: content?.length || 0,
        hasContent: Boolean(content),
        heroImageUrl,
        jobCount: jobs.length,
        previousBlogCount: previousBlogs.length,
      });
    }

    updateJob(taskId, {
      status: 'completed',
      currentStep: 'Blog generation complete!',
      progress: 100,
      blogContent: content,
      completedAt: new Date().toISOString(),
      connectionState: 'closed',
      connectionMessage: 'Live updates completed',
      connectionUpdatedAt: new Date().toISOString(),
    });

    if (state.activeConnectionId === taskId) {
      resetActiveConnection();
    }

    try {
      await blogService.updateBlogCompletion(taskId, 'completed', content, undefined, heroImageUrl);
    } catch (error) {
      logger.error('Failed to persist completion state', error);
    }

    const matchingJob = jobs.find((job) => job.id === taskId);
    if (matchingJob) {
      const blogData: BlogData = {
        id: taskId,
        userId: '',
        topic: matchingJob.topic,
        instructions: matchingJob.instructions,
        content,
        status: 'completed',
        progress: 100,
        currentStep: 'Blog generation complete!',
        error: null,
        createdAt: typeof matchingJob.createdAt === 'string'
          ? matchingJob.createdAt
          : new Date(matchingJob.createdAt).toISOString(),
        updatedAt: new Date().toISOString(),
        completedAt: new Date().toISOString(),
        heroImageUrl: heroImageUrl || null,
      };
      actions.setSelectedBlog(blogData);
      actions.setShowBlogModal(true);
    }

    deleteJob(taskId);

    try {
      await Promise.all([refetchStats(), fetchPreviousBlogs()]);
    } catch (error) {
      logger.error('Failed to refresh data after completion', error);
    }
  }, [actions, deleteJob, fetchPreviousBlogs, jobs, previousBlogs.length, refetchStats, resetActiveConnection, state.activeConnectionId, updateJob]);

  const handleTaskError = useCallback(async (taskId: string, errorMessage: string) => {
    const errorInfo: ErrorInfo = {
      error_type: 'generation_error',
      user_message: errorMessage,
      technical_details: errorMessage,
      is_recoverable: true,
      suggestions: ['Try a different topic', 'Check your connection'],
      timestamp: new Date().toISOString(),
      severity: 'error',
    };

    updateJob(taskId, {
      status: 'failed',
      currentStep: 'Generation failed',
      progress: 0,
      error: errorInfo,
      connectionState: 'error',
      connectionMessage: errorMessage,
      connectionUpdatedAt: new Date().toISOString(),
    });

    if (state.activeConnectionId === taskId) {
      resetActiveConnection();
    }

    try {
      await blogService.updateBlogCompletion(taskId, 'failed', undefined, errorInfo);
    } catch (error) {
      logger.error('Failed to persist error state', error);
    }
  }, [resetActiveConnection, state.activeConnectionId, updateJob]);

  const handleGenerateBlog = useCallback(async (topic: string, instructions: string) => {
    if (logger.shouldLog('debug')) {
      logger.debug('handleGenerateBlog:start', {
        topic,
        instructionsLength: instructions.length,
        canGenerate,
        activeConnectionId: state.activeConnectionId,
      });
    }

    const trimmedTopic = topic.trim();
    const trimmedInstructions = instructions.trim();

    if (!trimmedTopic) {
      actions.setGenerationError('Please enter a topic');
      return;
    }

    if (!canGenerate) {
      actions.setGenerationError('Monthly generation limit reached. Upgrade to Premium for more.');
      return;
    }

    if (state.activeConnectionId) {
      closeConnection();
      actions.setActiveConnectionId(null);
    }

    try {
      actions.setGenerationError(null);
      actions.setIsGenerating(true);
      actions.setCreatingNew(false);
      completedTasksRef.current.clear();
      firstUpdateReceivedRef.current = null;

      const taskId = await blogService.generateTaskId();

      const initialLog: LogEntry = {
        timestamp: new Date().toISOString(),
        step: 'initialization',
        message: `Blog generation started for topic: "${trimmedTopic}"${trimmedInstructions ? ` with instructions: "${trimmedInstructions}"` : ''}`,
        progress: 0,
      };

      actions.setTaskLogs({
        ...state.taskLogs,
        [taskId]: [initialLog],
      });

      createJob(taskId, trimmedTopic, trimmedInstructions);
      actions.setCurrentJobId(taskId);
      actions.setActiveConnectionId(taskId);

      const generationResponse = await blogService.generateBlog(trimmedTopic, trimmedInstructions, taskId);

      if (generationResponse.task_id !== taskId) {
        logger.warn('Task ID mismatch detected', {
          expectedTaskId: taskId,
          receivedTaskId: generationResponse.task_id,
        });
      }

      const connectionLog: LogEntry = {
        timestamp: new Date().toISOString(),
        step: 'connection',
        message: 'Setting up connection...',
        progress: 5,
      };

      actions.appendTaskLog(taskId, connectionLog);

      try {
        await connectToTaskStream(
          taskId,
          (updateTaskId: string, updates: Partial<JobState>) => {
            if (logger.shouldLog('debug')) {
              logger.debug('SSE Update received', { updateTaskId, updates });
            }
            updateJob(updateTaskId, updates);
            if (firstUpdateReceivedRef.current !== updateTaskId) {
              firstUpdateReceivedRef.current = updateTaskId;
            }
          },
          (completeTaskId: string, content: string, heroImageUrl?: string) => {
            actions.setIsGenerating(false);
            handleTaskCompletion(completeTaskId, content, heroImageUrl);
          },
          handleTaskError,
          (logTaskId: string, log: LogEntry) => {
            actions.appendTaskLog(logTaskId, log);
          },
          handleConnectionStateChange
        );
      } catch (connectionError) {
        logger.error('Failed to start SSE stream', connectionError);

        if (connectionError instanceof Error) {
          const wasAuthError = handleAuthError(connectionError);
          if (wasAuthError) {
            actions.setIsGenerating(false);
            return;
          }
        }

        actions.setGenerationError('Real-time updates unavailable, but your blog is being generated in the background. Refresh the page in a few minutes to see your completed blog.');
        actions.setIsGenerating(false);
      }
    } catch (error) {
      logger.error('Error starting blog generation', error);

      if (error instanceof Error) {
        const wasAuthError = handleAuthError(error);
        if (wasAuthError) {
          actions.setIsGenerating(false);
          return;
        }
      }

      const errorMessage = error instanceof Error ? error.message : 'Failed to start blog generation.';
      actions.setGenerationError(errorMessage);

      if (state.activeConnectionId) {
        actions.setActiveConnectionId(null);
      }

      actions.setIsGenerating(false);
    }
  }, [actions, canGenerate, closeConnection, completedTasksRef, connectToTaskStream, createJob, handleAuthError, handleTaskCompletion, handleTaskError, handleConnectionStateChange, state.activeConnectionId, state.taskLogs, updateJob]);

  // Recover any active jobs on initial load
  useEffect(() => {
    if (!isAuthenticated || isAuthLoading || isRecoveringRef.current) {
      return;
    }

    isRecoveringRef.current = true;

    const recoverActiveJobs = async () => {
      try {
        const activeTasks = await taskService.getActiveTasks();

        if (activeTasks.length === 0) {
          return;
        }

        for (const task of activeTasks) {
          const job = taskService.convertTaskToJob(task);
          addTemporaryJob(job);

          if (task.status === 'in_progress' && !state.currentJobId) {
            actions.setCurrentJobId(task.id);
            actions.setActiveConnectionId(task.id);

            try {
              await connectToTaskStream(
                task.id,
                (taskId: string, updates: Partial<JobState>) => updateJob(taskId, updates),
                handleTaskCompletion,
                handleTaskError,
                (logTaskId: string, log: LogEntry) => actions.appendTaskLog(logTaskId, log),
                handleConnectionStateChange
              );
            } catch (error) {
              logger.error(`Failed to reconnect to task ${task.id}`, error);
              actions.setGenerationError('Lost connection to active generation. Status may be outdated.');
            }
          }
        }
      } catch (error) {
        logger.error('Failed to recover active jobs', error);
      }
    };

    void recoverActiveJobs();
  }, [actions, addTemporaryJob, connectToTaskStream, handleConnectionStateChange, handleTaskCompletion, handleTaskError, isAuthLoading, isAuthenticated, state.currentJobId, updateJob]);

  // Clean up connection reference on unmount
  useEffect(() => closeConnection, [closeConnection]);

  const closeActiveConnection = useCallback(() => {
    closeConnection();
    completedTasksRef.current.clear();
    if (state.activeConnectionId) {
      updateJob(state.activeConnectionId, {
        connectionState: 'closed',
        connectionMessage: 'Live updates closed by user',
        connectionUpdatedAt: new Date().toISOString(),
      });
    }
    actions.setActiveConnectionId(null);
  }, [actions, closeConnection, completedTasksRef, state.activeConnectionId, updateJob]);

  return {
    handleGenerateBlog,
    closeActiveConnection,
  };
}
