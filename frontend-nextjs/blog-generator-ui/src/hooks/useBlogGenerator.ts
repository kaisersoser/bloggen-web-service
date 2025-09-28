"use client";

import { useEffect } from 'react';
import { useAuth, useRoleCheck } from '@/hooks/useAuth';
import { useUserStats } from '@/hooks/useUserStats';
import { useBlogManagement } from '@/hooks/useBlogManagement';
import { useGenerationStateManager } from '@/hooks/useGenerationStateManager';
import { useGenerationLifecycle } from '@/hooks/useGenerationLifecycle';
import { useGenerationUiState } from '@/hooks/useGenerationUiState';
import { useGenerationActions } from '@/hooks/useGenerationActions';

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
  } = state;

  const { canGenerate, currentJob } = useGenerationUiState({
    state,
    actions,
    jobs,
    stats,
    fetchPreviousBlogs,
    isAuthenticated,
    isAuthLoading: isLoading,
    canGenerateBlog,
  });

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

  const {
    handleJobClick,
    handleBlogClick,
    handleDeleteBlog,
    handleBulkDeleteBlogs,
    handleDeleteStuckTask,
    confirmDeleteBlog,
    handleNewBlog,
    clearTaskLogs,
  } = useGenerationActions({
    state,
    actions,
    previousBlogs,
    deleteBlog,
    deleteTask,
    fetchPreviousBlogs,
    closeActiveConnection,
  });

  useEffect(() => {
    return () => {
      if (state.activeConnectionId) {
        closeActiveConnection();
      }
    };
  }, [closeActiveConnection, state.activeConnectionId]);

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
