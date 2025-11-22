import { useState, useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { BlogData, JobState } from '@/types/blog';
import { logger } from '@/lib/logger';
import { blogService } from '@/lib/services/blog';
import { VERBOSE_LOGGING_ENABLED } from '@/lib/logger/env';

async function fetchPreviousBlogsFromApi(): Promise<BlogData[]> {
  const canLogVerbose = VERBOSE_LOGGING_ENABLED && logger.shouldLog('info');
  if (canLogVerbose) {
    logger.info('🔄 Fetching previous blogs from API');
  }

  const blogs = await blogService.getUserBlogs();

  if (canLogVerbose) {
    logger.info('📊 Fetched blogs from API', {
      blogs: blogs.map(b => ({
        id: b.id,
        topic: b.topic,
        status: b.status,
        hasContent: Boolean(b.content),
        hasHeroImage: Boolean(b.heroImageUrl)
      }))
    });
  }

  return blogs;
}

export function useBlogManagement() {
  const [jobs, setJobs] = useState<JobState[]>([]);
  // Local state for actively generating blogs (queued/in_progress)
  const [activeBlogs, setActiveBlogs] = useState<BlogData[]>([]);
  // Force re-render counter to trigger useMemo recalculation
  const [, forceUpdate] = useState(0);
  const queryClient = useQueryClient();

  const {
    data: persistedBlogs = [],
    isPending,
    isFetching,
  } = useQuery<BlogData[]>({
    queryKey: ['blogs'],
    queryFn: fetchPreviousBlogsFromApi,
    placeholderData: [],
    // Disable structural sharing to ensure React always sees new data
    structuralSharing: false,
  });

  const blogsLoading = isPending || (isFetching && persistedBlogs.length === 0);
  
  // Merge active blogs with persisted blogs (active blogs take precedence)
  const previousBlogs = useMemo(() => {
    const activeBlogIds = new Set(activeBlogs.map(b => b.id));
    const filtered = persistedBlogs.filter(b => !activeBlogIds.has(b.id));
    const merged = [...activeBlogs, ...filtered];
    logger.info('[useBlogManagement] Merged blogs', { 
      activeCount: activeBlogs.length, 
      persistedCount: persistedBlogs.length,
      mergedCount: merged.length,
      activeBlogs: activeBlogs.map(b => ({ id: b.id, status: b.status }))
    });
    return merged;
  }, [activeBlogs, persistedBlogs]);

  const updateJob = useCallback((jobId: string, updates: Partial<JobState>) => {
    setJobs(prevJobs => 
      prevJobs.map(job => 
        job.id === jobId ? { ...job, ...updates } : job
      )
    );
  }, []);

  const addLogToJob = useCallback((jobId: string, log: string, timestamp: string) => {
    const logEntry = {
      task_id: jobId,
      log: `📊 ${log}`,
      timestamp
    };
    
    setJobs(prevJobs => 
      prevJobs.map(job => 
        job.id === jobId 
          ? { ...job, logs: [...job.logs, logEntry] }
          : job
      )
    );
  }, []);

  const createJob = useCallback((jobId: string, topic: string, instructions: string): JobState => {
    const newJob: JobState = {
      id: jobId,
      topic,
      instructions,
      status: 'queued',
      progress: 0,
      currentStep: 'Starting...',
      logs: [],
      blogContent: '',
      error: null,
      createdAt: new Date().toISOString(),
      connectionState: 'connecting',
      connectionMessage: 'Preparing live updates…',
      connectionUpdatedAt: new Date().toISOString()
    };
    
    setJobs(prevJobs => [...prevJobs, newJob]);
    return newJob;
  }, []);

  const deleteJob = useCallback((jobId: string) => {
    setJobs(prevJobs => prevJobs.filter(job => job.id !== jobId));
  }, []);

  const fetchPreviousBlogs = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ['blogs'] });
  }, [queryClient]);

  const deleteBlog = useCallback(async (blogId: string) => {
    try {
      await blogService.deleteBlog(blogId);
      queryClient.setQueryData<BlogData[]>(['blogs'], (prev = []) =>
        prev.filter(blog => blog.id !== blogId)
      );
      return true;
    } catch (error) {
      logger.error('Error deleting blog', error);
      return false;
    }
  }, [queryClient]);

  const deleteTask = useCallback(async (taskId: string): Promise<void> => {
    if (!taskId) {
      throw new Error('Task ID is required');
    }
    
    try {
      await blogService.deleteStuckTask(taskId);
      if (VERBOSE_LOGGING_ENABLED && logger.shouldLog('info')) {
        logger.info('Stuck task deleted successfully', { taskId });
      }
    } catch (error) {
      logger.error('Error deleting stuck task', error);
      throw error;
    }
  }, []);

  const convertBlogToJob = useCallback((blog: BlogData): JobState => ({
    id: blog.id,
    topic: blog.topic,
    instructions: blog.instructions || '',
    status: blog.status.toLowerCase() as JobState['status'],
    progress: blog.progress,
    currentStep: blog.currentStep || 'Completed',
    logs: [],
    blogContent: blog.content || '',
    error: blog.error,
    createdAt: blog.createdAt,
    completedAt: blog.completedAt || undefined,
    connectionState: 'closed',
    connectionMessage: 'Live updates ended',
    connectionUpdatedAt: new Date().toISOString()
  }), []);

  const addTemporaryJob = useCallback((job: JobState) => {
    setJobs(prevJobs => {
      const existingIndex = prevJobs.findIndex(j => j.id === job.id);
      if (existingIndex >= 0) {
        const newJobs = [...prevJobs];
        newJobs[existingIndex] = job;
        return newJobs;
      } else {
        return [...prevJobs, job];
      }
    });
  }, []);

  // Add a temporary blog to activeBlogs immediately when generation starts
  const addTemporaryBlog = useCallback((blog: BlogData) => {
    logger.info('[addTemporaryBlog] Adding active blog', { blogId: blog.id, status: blog.status });
    
    setActiveBlogs(prev => {
      // Check if blog already exists
      const existingIndex = prev.findIndex(b => b.id === blog.id);
      if (existingIndex >= 0) {
        // Update existing
        const newBlogs = [...prev];
        newBlogs[existingIndex] = { ...newBlogs[existingIndex], ...blog };
        return newBlogs;
      } else {
        // Add new blog at the beginning
        return [blog, ...prev];
      }
    });
  }, []);

  // Update a temporary blog's status/progress in activeBlogs
  const updateTemporaryBlog = useCallback((blogId: string, updates: Partial<BlogData>) => {
    logger.info('[updateTemporaryBlog] Updating active blog', { blogId, updates });
    
    setActiveBlogs(prev => {
      const updated = prev.map(blog => {
        if (blog.id === blogId) {
          const newBlog = { ...blog, ...updates, updatedAt: new Date().toISOString() };
          logger.info('[updateTemporaryBlog] Updated blog in activeBlogs', { 
            blogId, 
            oldStatus: blog.status, 
            newStatus: newBlog.status 
          });
          return newBlog;
        }
        return blog;
      });
      return updated;
    });
    
    // Force a re-render to ensure UI updates
    forceUpdate(n => n + 1);
  }, [forceUpdate]);

  // Remove blog from activeBlogs and optionally refresh persisted blogs
  const removeTemporaryBlog = useCallback((blogId: string, shouldRefresh: boolean = false) => {
    logger.info('[removeTemporaryBlog] Removing from activeBlogs', { blogId, shouldRefresh });
    
    setActiveBlogs(prev => prev.filter(blog => blog.id !== blogId));
    
    if (shouldRefresh) {
      // Refresh persisted blogs from backend
      queryClient.invalidateQueries({ queryKey: ['blogs'] });
    }
  }, [queryClient]);

  return {
    jobs,
    previousBlogs,
    blogsLoading,
    updateJob,
    addLogToJob,
    createJob,
    deleteJob,
    fetchPreviousBlogs,
    deleteBlog,
    deleteTask,
    convertBlogToJob,
    addTemporaryJob,
    addTemporaryBlog,
    updateTemporaryBlog,
    removeTemporaryBlog
  };
}
