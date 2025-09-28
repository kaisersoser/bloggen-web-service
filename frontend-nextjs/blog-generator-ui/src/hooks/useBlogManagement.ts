import { useState, useCallback } from 'react';
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
  const queryClient = useQueryClient();

  const {
    data: previousBlogs = [],
    isPending,
    isFetching,
  } = useQuery<BlogData[]>({
    queryKey: ['blogs'],
    queryFn: fetchPreviousBlogsFromApi,
    placeholderData: [],
  });

  const blogsLoading = isPending || (isFetching && previousBlogs.length === 0);

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
    addTemporaryJob
  };
}
