import { useEffect, useMemo, useCallback } from 'react';
import { useAuth, useRoleCheck } from '@/hooks/useAuth';
import { useUserStats } from '@/hooks/useUserStats';
import { useBlogManagement } from '@/hooks/useBlogManagement';
import { logger } from '@/lib/logger';
import type { BlogData } from '@/types/blog';
import { useGenerationStateManager } from '@/hooks/useGenerationStateManager';
import { useGenerationLifecycle } from '@/hooks/useGenerationLifecycle';

export function useBlogGenerator() {
  const { isAuthenticated, isLoading } = useAuth();
  const { canGenerateBlog, isFree } = useRoleCheck();
  const { stats, loading: statsLoading, refetch: refetchStats } = useUserStats();
  const {
    jobs,
    previousBlogs,
    blogsLoading,
    updateJob,
    createJob,
    fetchPreviousBlogs,
    deleteBlog,
    deleteTask,
    deleteJob,
    addTemporaryJob,
  } = useBlogManagement();

  const { state, actions } = useGenerationStateManager();
  const {
    currentJobId,
    generationError,
    isGenerating,
    activeConnectionId,
    taskLogs,
    showDeleteDialog,
    blogToDelete,
    isDeleting,
    selectedBlog,
    showBlogModal,
    creatingNew,
  } = state;

  const canGenerate = useMemo(() => {
    if (!stats) {
      return canGenerateBlog();
    }
    return stats.remainingGenerations > 0 || stats.monthlyLimit === -1;
  }, [stats, canGenerateBlog]);

  const { handleGenerateBlog, closeActiveConnection } = useGenerationLifecycle({
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
    isAuthLoading: isLoading,
  });

  const currentJob = useMemo(() => {
    if (!currentJobId) {
      return null;
    }
    return jobs.find((job) => job.id === currentJobId) || null;
  }, [jobs, currentJobId]);

  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      void fetchPreviousBlogs();
    }
  }, [fetchPreviousBlogs, isAuthenticated, isLoading]);

  useEffect(() => {
    if (jobs.length > 0 && !currentJobId && !creatingNew) {
      actions.setCurrentJobId(jobs[jobs.length - 1].id);
    }
  }, [actions, creatingNew, currentJobId, jobs]);

  useEffect(() => {
    actions.setGenerationError(null);
  }, [actions, currentJobId]);

  useEffect(() => {
    if (generationError && isGenerating) {
      logger.warn('Resetting isGenerating due to error state');
      actions.setIsGenerating(false);
    }
  }, [actions, generationError, isGenerating]);

  useEffect(() => {
    return () => {
      if (state.activeConnectionId) {
        closeActiveConnection();
      }
    };
  }, [closeActiveConnection, state.activeConnectionId]);

  const handleJobClick = useCallback((jobId: string) => {
    if (activeConnectionId && activeConnectionId !== jobId) {
      closeActiveConnection();
    }
    actions.setCurrentJobId(jobId);
    actions.setGenerationError(null);
  }, [actions, activeConnectionId, closeActiveConnection]);

  const handleBlogClick = useCallback((blog: BlogData) => {
    actions.setSelectedBlog(blog);
    actions.setShowBlogModal(true);
  }, [actions]);

  const handleDeleteBlog = useCallback((blogId: string) => {
    const blog = previousBlogs.find((item) => item.id === blogId);
    if (blog) {
      actions.setBlogToDelete(blog);
      actions.setShowDeleteDialog(true);
    }
  }, [actions, previousBlogs]);

  const handleBulkDeleteBlogs = useCallback(async (blogIds: string[]) => {
    try {
      const results = await Promise.all(blogIds.map((id) => deleteBlog(id)));
      const succeeded = results.filter(Boolean).length;

      if (succeeded === blogIds.length) {
        await fetchPreviousBlogs();
      } else {
        actions.setGenerationError(`Failed to delete ${blogIds.length - succeeded} blog(s).`);
      }
    } catch (error) {
      logger.error('Bulk delete failed', error);
      actions.setGenerationError('Bulk delete failed.');
    }
  }, [actions, deleteBlog, fetchPreviousBlogs]);

  const handleDeleteStuckTask = useCallback(async (taskId: string) => {
    try {
      await deleteTask(taskId);

      if (currentJobId === taskId) {
        actions.setCurrentJobId(null);
        actions.setGenerationError(null);
      }

      if (activeConnectionId === taskId) {
        closeActiveConnection();
      }

      await fetchPreviousBlogs();
    } catch (error) {
      logger.error('Delete stuck task failed', error);
      actions.setGenerationError('Failed to delete stuck task.');
    }
  }, [actions, activeConnectionId, closeActiveConnection, currentJobId, deleteTask, fetchPreviousBlogs]);

  const confirmDeleteBlog = useCallback(async () => {
    if (!blogToDelete) {
      return;
    }

    actions.setIsDeleting(true);

    try {
      const success = await deleteBlog(blogToDelete.id);
      if (success) {
        actions.setShowDeleteDialog(false);
        if (currentJobId === blogToDelete.id) {
          actions.setCurrentJobId(null);
          actions.setGenerationError(null);
        }
      }
    } catch (error) {
      logger.error('Delete blog failed', error);
      actions.setGenerationError('Failed to delete blog.');
    } finally {
      actions.setIsDeleting(false);
    }
  }, [actions, blogToDelete, currentJobId, deleteBlog]);

  const handleNewBlog = useCallback(() => {
    if (isGenerating && activeConnectionId) {
      return;
    }

    actions.setCreatingNew(true);
    actions.setCurrentJobId(null);
    actions.setGenerationError(null);
    actions.setSelectedBlog(null);
    actions.setShowBlogModal(false);
  }, [actions, activeConnectionId, isGenerating]);

  const clearTaskLogs = useCallback(() => {
    actions.clearTaskLogs();
    if (logger.shouldLog('debug')) {
      logger.debug('Task logs cleared via clearTaskLogs callback');
    }
  }, [actions]);

  return {
    isAuthenticated,
    isLoading,
    stats,
    statsLoading,
    isFree,
    jobs,
    previousBlogs,
    blogsLoading,
    currentJobId,
    currentJob,
    generationError,
    isGenerating,
    activeConnectionId,
    taskLogs,
    showDeleteDialog,
    blogToDelete,
    isDeleting,
    selectedBlog,
    showBlogModal,
    canGenerate,
    handleGenerateBlog,
    handleJobClick,
    handleBlogClick,
    handleDeleteBlog,
    handleBulkDeleteBlogs,
    handleDeleteStuckTask,
    confirmDeleteBlog,
    handleNewBlog,
  clearTaskLogs,
    setShowDeleteDialog: actions.setShowDeleteDialog,
    setBlogToDelete: actions.setBlogToDelete,
    setIsDeleting: actions.setIsDeleting,
    setGenerationError: actions.setGenerationError,
    setSelectedBlog: actions.setSelectedBlog,
    setShowBlogModal: actions.setShowBlogModal,
    refetchStats,
    fetchPreviousBlogs,
  } as const;
}
