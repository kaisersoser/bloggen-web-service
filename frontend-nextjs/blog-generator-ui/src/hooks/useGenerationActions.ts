import { useCallback } from 'react';
import { logger } from '@/lib/logger';
import type { BlogData } from '@/types/blog';
import type { GenerationState, GenerationStateActions } from '@/hooks/useGenerationStateManager';

interface UseGenerationActionsParams {
  state: GenerationState;
  actions: GenerationStateActions;
  previousBlogs: BlogData[];
  deleteBlog: (blogId: string) => Promise<boolean>;
  deleteTask: (taskId: string) => Promise<void>;
  fetchPreviousBlogs: () => Promise<unknown>;
  closeActiveConnection: () => void;
}

export function useGenerationActions({
  state,
  actions,
  previousBlogs,
  deleteBlog,
  deleteTask,
  fetchPreviousBlogs,
  closeActiveConnection,
}: UseGenerationActionsParams) {
  const handleJobClick = useCallback((jobId: string) => {
    if (state.activeConnectionId && state.activeConnectionId !== jobId) {
      closeActiveConnection();
    }
    actions.setCurrentJobId(jobId);
    actions.setGenerationError(null);
  }, [actions, closeActiveConnection, state.activeConnectionId]);

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

      if (state.currentJobId === taskId) {
        actions.setCurrentJobId(null);
        actions.setGenerationError(null);
      }

      if (state.activeConnectionId === taskId) {
        closeActiveConnection();
      }

      await fetchPreviousBlogs();
    } catch (error) {
      logger.error('Delete stuck task failed', error);
      actions.setGenerationError('Failed to delete stuck task.');
    }
  }, [actions, closeActiveConnection, deleteTask, fetchPreviousBlogs, state.activeConnectionId, state.currentJobId]);

  const confirmDeleteBlog = useCallback(async () => {
    if (!state.blogToDelete) {
      return;
    }

    actions.setIsDeleting(true);

    try {
      const success = await deleteBlog(state.blogToDelete.id);
      if (success) {
        actions.setShowDeleteDialog(false);
        if (state.currentJobId === state.blogToDelete.id) {
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
  }, [actions, deleteBlog, state.blogToDelete, state.currentJobId]);

  const handleNewBlog = useCallback(() => {
    if (state.isGenerating && state.activeConnectionId) {
      return;
    }

    actions.setCreatingNew(true);
    actions.setCurrentJobId(null);
    actions.setGenerationError(null);
    actions.setSelectedBlog(null);
    actions.setShowBlogModal(false);
  }, [actions, state.activeConnectionId, state.isGenerating]);

  const clearTaskLogs = useCallback(() => {
    actions.clearTaskLogs();
    if (logger.shouldLog('debug')) {
      logger.debug('Task logs cleared via clearTaskLogs callback');
    }
  }, [actions]);

  return {
    handleJobClick,
    handleBlogClick,
    handleDeleteBlog,
    handleBulkDeleteBlogs,
    handleDeleteStuckTask,
    confirmDeleteBlog,
    handleNewBlog,
    clearTaskLogs,
  } as const;
}
