import { useEffect, useMemo } from 'react';
import { logger } from '@/lib/logger';
import type { JobState } from '@/types/blog';
import type { GenerationState, GenerationStateActions } from '@/hooks/useGenerationStateManager';

interface UserStats {
  monthlyGenerations: number;
  monthlyLimit: number;
  remainingGenerations: number;
  role: string;
  lastGenerationReset: string;
}

interface UseGenerationUiStateParams {
  state: GenerationState;
  actions: GenerationStateActions;
  jobs: JobState[];
  stats: UserStats | null;
  fetchPreviousBlogs: () => Promise<unknown>;
  isAuthenticated: boolean;
  isAuthLoading: boolean;
  canGenerateBlog: () => boolean;
}

export function useGenerationUiState({
  state,
  actions,
  jobs,
  stats,
  fetchPreviousBlogs,
  isAuthenticated,
  isAuthLoading,
  canGenerateBlog,
}: UseGenerationUiStateParams) {
  const canGenerate = useMemo(() => {
    if (!stats) {
      return canGenerateBlog();
    }
    return stats.remainingGenerations > 0 || stats.monthlyLimit === -1;
  }, [stats, canGenerateBlog]);

  const currentJob = useMemo(() => {
    if (!state.currentJobId) {
      return null;
    }
    return jobs.find((job) => job.id === state.currentJobId) || null;
  }, [jobs, state.currentJobId]);

  useEffect(() => {
    if (isAuthenticated && !isAuthLoading) {
      void fetchPreviousBlogs();
    }
  }, [fetchPreviousBlogs, isAuthenticated, isAuthLoading]);

  useEffect(() => {
    if (jobs.length > 0 && !state.currentJobId && !state.creatingNew) {
      actions.setCurrentJobId(jobs[jobs.length - 1].id);
    }
  }, [actions, jobs, state.currentJobId, state.creatingNew]);

  useEffect(() => {
    actions.setGenerationError(null);
  }, [actions, state.currentJobId]);

  useEffect(() => {
    if (state.generationError && state.isGenerating) {
      logger.warn('Resetting isGenerating due to error state');
      actions.setIsGenerating(false);
    }
  }, [actions, state.generationError, state.isGenerating]);

  return {
    canGenerate,
    currentJob,
  } as const;
}
