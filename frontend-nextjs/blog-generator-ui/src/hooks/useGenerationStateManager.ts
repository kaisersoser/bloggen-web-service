"use client";

import { useMemo } from 'react';
import {
  useGenerationStore,
  type GenerationState,
  type GenerationStateActions,
} from '@/store/useGenerationStore';

export type { GenerationState, GenerationStateActions } from '@/store/useGenerationStore';

export function useGenerationStateManager() {
  const currentJobId = useGenerationStore((store) => store.currentJobId);
  const generationError = useGenerationStore((store) => store.generationError);
  const isGenerating = useGenerationStore((store) => store.isGenerating);
  const activeConnectionId = useGenerationStore((store) => store.activeConnectionId);
  const taskLogs = useGenerationStore((store) => store.taskLogs);
  const showDeleteDialog = useGenerationStore((store) => store.showDeleteDialog);
  const blogToDelete = useGenerationStore((store) => store.blogToDelete);
  const isDeleting = useGenerationStore((store) => store.isDeleting);
  const selectedBlog = useGenerationStore((store) => store.selectedBlog);
  const showBlogModal = useGenerationStore((store) => store.showBlogModal);
  const creatingNew = useGenerationStore((store) => store.creatingNew);

  const state = useMemo(
    () => ({
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
    }),
    [
      activeConnectionId,
      blogToDelete,
      creatingNew,
      currentJobId,
      generationError,
      isDeleting,
      isGenerating,
      selectedBlog,
      showDeleteDialog,
  showBlogModal,
      taskLogs,
    ]
  );

  const actions = useMemo<GenerationStateActions>(() => ({
    setCurrentJobId: useGenerationStore.getState().setCurrentJobId,
    setGenerationError: useGenerationStore.getState().setGenerationError,
    setIsGenerating: useGenerationStore.getState().setIsGenerating,
    setActiveConnectionId: useGenerationStore.getState().setActiveConnectionId,
    setTaskLogs: useGenerationStore.getState().setTaskLogs,
    appendTaskLog: useGenerationStore.getState().appendTaskLog,
    clearTaskLogs: useGenerationStore.getState().clearTaskLogs,
    setShowDeleteDialog: useGenerationStore.getState().setShowDeleteDialog,
    setBlogToDelete: useGenerationStore.getState().setBlogToDelete,
    setIsDeleting: useGenerationStore.getState().setIsDeleting,
    setSelectedBlog: useGenerationStore.getState().setSelectedBlog,
    setShowBlogModal: useGenerationStore.getState().setShowBlogModal,
    setCreatingNew: useGenerationStore.getState().setCreatingNew,
  }), []);

  return { state, actions } as const;
}
