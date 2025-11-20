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
  addTemporaryBlog: (blog: BlogData) => void;
  updateTemporaryBlog: (blogId: string, updates: Partial<BlogData>) => void;
  removeTemporaryBlog: (blogId: string) => void;
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
  addTemporaryBlog,
  updateTemporaryBlog,
  removeTemporaryBlog,
  isAuthenticated,
  isAuthLoading,
}: UseGenerationLifecycleParams): UseGenerationLifecycleReturn {
  // Polling state - only poll when no SSE connection is active
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const isPollingRef = useRef(false);
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
      
      // Immediately update the temporary blog card to completed state
      updateTemporaryBlog(taskId, {
        status: 'completed',
        progress: 100,
        currentStep: 'Blog generation complete!',
        content,
        heroImageUrl: heroImageUrl || null,
        completedAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
      
      actions.setSelectedBlog(blogData);
      actions.setShowBlogModal(true);
    }

    deleteJob(taskId);

    // Refresh blog list in background to get the persisted version from backend
    setTimeout(async () => {
      try {
        await Promise.all([refetchStats(), fetchPreviousBlogs()]);
      } catch (error) {
        logger.error('Failed to refresh data after completion', error);
      }
    }, 500);
  }, [actions, deleteJob, fetchPreviousBlogs, jobs, previousBlogs.length, refetchStats, resetActiveConnection, state.activeConnectionId, updateJob, updateTemporaryBlog]);

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
    
    // Immediately update the temporary blog card to failed state
    updateTemporaryBlog(taskId, {
      status: 'failed',
      progress: 0,
      currentStep: 'Generation failed',
      error: errorInfo,
      updatedAt: new Date().toISOString(),
    });

    if (state.activeConnectionId === taskId) {
      resetActiveConnection();
    }

    try {
      await blogService.updateBlogCompletion(taskId, 'failed', undefined, errorInfo);
      // Refresh to get updated blog from backend
      await fetchPreviousBlogs();
    } catch (error) {
      logger.error('Failed to persist error state', error);
    }
  }, [fetchPreviousBlogs, resetActiveConnection, state.activeConnectionId, updateJob, updateTemporaryBlog]);

  // Start polling for queued blogs that transition to IN_PROGRESS
  const startPollingForNextBlog = useCallback(() => {
    // Don't start polling if already polling or if SSE connection is active
    if (isPollingRef.current || state.activeConnectionId) {
      return;
    }

    isPollingRef.current = true;

    pollingIntervalRef.current = setInterval(async () => {
      try {
        // Find all queued blogs (both from jobs and temporary blogs)
        const queuedBlogs = jobs.filter(job => job.status === 'queued');
        const queuedTempBlogs = previousBlogs.filter(blog => blog.status === 'queued');
        
        // Check each queued blog's status
        for (const blog of [...queuedBlogs, ...queuedTempBlogs]) {
          const taskId = blog.id;
          
          try {
            const statusResponse = await blogService.getBlogStatus(taskId);
            
            // If status changed to IN_PROGRESS, stop polling and connect SSE
            if (statusResponse.status === 'IN_PROGRESS') {
              logger.info(`Blog ${taskId} started processing, connecting SSE`, statusResponse);
              
              // Stop polling
              stopPollingForNextBlog();
              
              // Update blog card to show in_progress (lowercase for frontend display)
              updateTemporaryBlog(taskId, {
                status: 'in_progress',
                progress: statusResponse.progress || 0,
                currentStep: statusResponse.currentStep || 'Processing...',
                updatedAt: new Date().toISOString(),
              });
              
              updateJob(taskId, {
                status: 'in_progress',
                progress: statusResponse.progress || 0,
                currentStep: statusResponse.currentStep || 'Processing...',
              });
              
              // Now create SSE connection
              await connectToTaskStream(
                taskId,
                (updateTaskId: string, updates: Partial<JobState>) => {
                  if (logger.shouldLog('debug')) {
                    logger.debug('SSE Update received', { updateTaskId, updates });
                  }
                  updateJob(updateTaskId, updates);
                  
                  updateTemporaryBlog(updateTaskId, {
                    status: updates.status || 'in_progress',
                    progress: updates.progress,
                    currentStep: updates.currentStep,
                    updatedAt: new Date().toISOString(),
                  });
                  
                  if (firstUpdateReceivedRef.current !== updateTaskId) {
                    firstUpdateReceivedRef.current = updateTaskId;
                  }
                },
                (completeTaskId: string, content: string, heroImageUrl?: string) => {
                  handleTaskCompletion(completeTaskId, content, heroImageUrl);
                  // After completion, resume polling for next queued blog
                  startPollingForNextBlog();
                },
                (errorTaskId: string, errorMessage: string) => {
                  handleTaskError(errorTaskId, errorMessage);
                  // After error, resume polling for next queued blog
                  startPollingForNextBlog();
                },
                (logTaskId: string, log: LogEntry) => {
                  actions.appendTaskLog(logTaskId, log);
                },
                handleConnectionStateChange
              );
              
              actions.setActiveConnectionId(taskId);
              
              // Only connect to one blog at a time
              break;
            }
          } catch (error) {
            logger.error(`Error checking status for blog ${taskId}`, error);
          }
        }
        
        // If no queued blogs found, stop polling
        if (queuedBlogs.length === 0 && queuedTempBlogs.length === 0) {
          stopPollingForNextBlog();
        }
      } catch (error) {
        logger.error('Error in polling loop', error);
      }
    }, 2000); // Poll every 2 seconds

    if (logger.shouldLog('debug')) {
      logger.debug('Started polling for next blog in queue');
    }
  }, [state.activeConnectionId, jobs, previousBlogs, updateJob, updateTemporaryBlog, actions, connectToTaskStream, handleConnectionStateChange, handleTaskCompletion, handleTaskError]);

  const stopPollingForNextBlog = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
    isPollingRef.current = false;
    
    if (logger.shouldLog('debug')) {
      logger.debug('Stopped polling for next blog');
    }
  }, []);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      stopPollingForNextBlog();
    };
  }, [stopPollingForNextBlog]);

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

    // Don't close existing connections - we support multiple concurrent generations
    // if (state.activeConnectionId) {
    //   closeConnection();
    //   actions.setActiveConnectionId(null);
    // }

    try {
      actions.setGenerationError(null);
      // Don't block the form - user can submit multiple blogs
      // actions.setIsGenerating(true); // REMOVED - no need to block
      actions.setCreatingNew(false);
      // Don't clear completed tasks - we track multiple
      // completedTasksRef.current.clear();
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
      // Track this as an active connection (we support multiple now)
      // Don't overwrite - just add to the list
      if (!state.activeConnectionId) {
        actions.setActiveConnectionId(taskId);
      }

      // Create temporary blog card immediately so it appears in the UI
      // Start with 'queued' status - backend will update to 'in_progress' when it starts processing
      const temporaryBlog: BlogData = {
        id: taskId,
        userId: '',
        topic: trimmedTopic,
        instructions: trimmedInstructions || null,
        content: null,
        status: 'queued',
        progress: 0,
        currentStep: 'Queued for generation...',
        error: null,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        completedAt: null,
        heroImageUrl: null,
        taskId: taskId,
      };
      addTemporaryBlog(temporaryBlog);

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

      // Don't create SSE connection immediately - wait for backend to start processing
      // Start polling to detect when this blog transitions from QUEUED to IN_PROGRESS
      startPollingForNextBlog();
      
      if (logger.shouldLog('debug')) {
        logger.debug('Started polling for blog to begin processing', { taskId });
      }
    } catch (error) {
      logger.error('Error starting blog generation', error);

      if (error instanceof Error) {
        const wasAuthError = handleAuthError(error);
        if (wasAuthError) {
          return;
        }
      }

      const errorMessage = error instanceof Error ? error.message : 'Failed to start blog generation.';
      actions.setGenerationError(errorMessage);

      if (state.activeConnectionId) {
        actions.setActiveConnectionId(null);
      }
    }
  }, [actions, addTemporaryBlog, canGenerate, createJob, handleAuthError, startPollingForNextBlog, state.activeConnectionId, state.taskLogs, updateTemporaryBlog]);

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
