// QUICK FIX 3: Lightweight State Management
// src/hooks/useLightweightBlogState.ts

import { useState, useCallback, useMemo } from 'react';
import { BlogData, JobState } from '@/types/blog';

interface LightweightBlogState {
  blogs: BlogData[];
  jobs: JobState[];
  currentJobId: string | null;
  isGenerating: boolean;
}

export function useLightweightBlogState() {
  const [state, setState] = useState<LightweightBlogState>({
    blogs: [],
    jobs: [],
    currentJobId: null,
    isGenerating: false
  });

  // Optimized updates using functional setState
  const updateBlogs = useCallback((blogs: BlogData[]) => {
    setState(prev => ({ ...prev, blogs }));
  }, []);

  const updateJob = useCallback((jobId: string, updates: Partial<JobState>) => {
    setState(prev => ({
      ...prev,
      jobs: prev.jobs.map(job => 
        job.id === jobId ? { ...job, ...updates } : job
      )
    }));
  }, []);

  const setCurrentJobId = useCallback((jobId: string | null) => {
    setState(prev => ({ ...prev, currentJobId: jobId }));
  }, []);

  const setIsGenerating = useCallback((isGenerating: boolean) => {
    setState(prev => ({ ...prev, isGenerating }));
  }, []);

  // Memoized selectors to prevent unnecessary re-renders
  const currentJob = useMemo(() => 
    state.currentJobId ? state.jobs.find(j => j.id === state.currentJobId) || null : null,
    [state.jobs, state.currentJobId]
  );

  const inProgressJobs = useMemo(() => 
    state.jobs.filter(job => job.status === 'in_progress'),
    [state.jobs]
  );

  return {
    // State
    blogs: state.blogs,
    jobs: state.jobs,
    currentJobId: state.currentJobId,
    isGenerating: state.isGenerating,
    
    // Computed
    currentJob,
    inProgressJobs,
    
    // Actions
    updateBlogs,
    updateJob,
    setCurrentJobId,
    setIsGenerating
  };
}
