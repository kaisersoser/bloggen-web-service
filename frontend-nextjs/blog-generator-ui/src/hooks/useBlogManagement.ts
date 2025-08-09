import { useState, useCallback } from 'react';
import { BlogData, JobState } from '@/types/blog';
import { blogService } from '@/lib/services/blog';

export function useBlogManagement() {
  const [jobs, setJobs] = useState<JobState[]>([]);
  const [previousBlogs, setPreviousBlogs] = useState<BlogData[]>([]);
  const [blogsLoading, setBlogsLoading] = useState(false);

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
      createdAt: new Date().toISOString()
    };
    
    setJobs(prevJobs => [...prevJobs, newJob]);
    return newJob;
  }, []);

  const deleteJob = useCallback((jobId: string) => {
    setJobs(prevJobs => prevJobs.filter(job => job.id !== jobId));
  }, []);

  const fetchPreviousBlogs = useCallback(async () => {
    try {
      setBlogsLoading(true);
      const blogs = await blogService.getUserBlogs();
      setPreviousBlogs(blogs);
    } catch (error) {
      console.error('Error fetching previous blogs:', error);
    } finally {
      setBlogsLoading(false);
    }
  }, []);

  const deleteBlog = useCallback(async (blogId: string) => {
    try {
      await blogService.deleteBlog(blogId);
      setPreviousBlogs(prevBlogs => 
        prevBlogs.filter(blog => blog.id !== blogId)
      );
      return true;
    } catch (error) {
      console.error('Error deleting blog:', error);
      return false;
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
    completedAt: blog.completedAt || undefined
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
    convertBlogToJob,
    addTemporaryJob
  };
}
