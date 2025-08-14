import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useAuth, useRoleCheck } from '@/hooks/useAuth';
import { useUserStats } from '@/hooks/useUserStats';
import { useBlogManagement } from '@/hooks/useBlogManagement';
import { useWebSocketConnection } from '@/hooks/useWebSocketConnection';
import { blogService } from '@/lib/services/blog';
import { taskService } from '@/lib/services/task';
import { BlogData, ErrorInfo, LogEntry, JobState } from '@/types/blog';
// PromptConfig import removed (unused after refactor)

export function useBlogGenerator() {
  const { isAuthenticated, isLoading } = useAuth();
  const { canGenerateBlog, isFree } = useRoleCheck();
  const { stats, loading: statsLoading, refetch: refetchStats } = useUserStats();
  const { jobs, previousBlogs, blogsLoading, updateJob, createJob, fetchPreviousBlogs, deleteBlog, addTemporaryJob } = useBlogManagement();
  const { connectToTaskStream, closeConnection, completedTasksRef } = useWebSocketConnection();

  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeConnectionId, setActiveConnectionId] = useState<string | null>(null);
  const [taskLogs, setTaskLogs] = useState<Record<string, LogEntry[]>>({});
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [blogToDelete, setBlogToDelete] = useState<BlogData | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // Track if we've received the first WebSocket update to avoid multiple setIsGenerating(false) calls
  const firstUpdateReceivedRef = useRef<string | null>(null);
  const [selectedBlog, setSelectedBlog] = useState<BlogData | null>(null);
  const [showBlogModal, setShowBlogModal] = useState(false);
  // Tracks whether user explicitly requested starting a new blog (prevents auto re-selecting last job)
  const [creatingNew, setCreatingNew] = useState(false);

  const currentJob = useMemo(() => currentJobId ? (jobs.find(j => j.id === currentJobId) || null) : null, [jobs, currentJobId]);
  const canGenerate = useMemo(() => { if (!stats) return canGenerateBlog(); return stats.remainingGenerations > 0 || stats.monthlyLimit === -1; }, [stats, canGenerateBlog]);

  useEffect(() => { if (isAuthenticated && !isLoading) fetchPreviousBlogs(); }, [isAuthenticated, isLoading, fetchPreviousBlogs]);
  // Auto-select most recent job only if user isn't intentionally starting a new one
  useEffect(() => {
    if (jobs.length > 0 && !currentJobId && !creatingNew) {
      setCurrentJobId(jobs[jobs.length - 1].id);
    }
  }, [jobs, currentJobId, creatingNew]);
  useEffect(() => { setGenerationError(null); }, [currentJobId]);
  useEffect(() => () => { if (activeConnectionId) { closeConnection(); setActiveConnectionId(null); } }, [activeConnectionId, closeConnection]);

  const handleTaskCompletion = useCallback(async (taskId: string, content: string, heroImageUrl?: string) => {
    updateJob(taskId, { status: 'completed', currentStep: 'Blog generation complete!', progress: 100, blogContent: content, completedAt: new Date().toISOString() });
    if (activeConnectionId === taskId) {
      setActiveConnectionId(null);
      setIsGenerating(false); // Reset generating state on completion
    }
    const job = jobs.find(j => j.id === taskId);
    if (job) {
      const blogData: BlogData = { id: taskId, userId: '', topic: job.topic, instructions: job.instructions, content, status: 'completed', progress: 100, currentStep: 'Blog generation complete!', error: null, createdAt: typeof job.createdAt === 'string' ? job.createdAt : new Date(job.createdAt).toISOString(), updatedAt: new Date().toISOString(), completedAt: new Date().toISOString(), heroImageUrl: heroImageUrl || null } as any;
      setSelectedBlog(blogData); setShowBlogModal(true);
    }
    try { await blogService.updateBlogCompletion(taskId, 'completed', content, undefined, heroImageUrl); await Promise.all([refetchStats(), fetchPreviousBlogs()]); }
    catch (err) { console.error('Failed to persist completion:', err); updateJob(taskId, { status: 'failed', currentStep: 'Failed to save blog', error: { error_type: 'save_error', user_message: 'Blog saved locally but persistence failed.', technical_details: err instanceof Error ? err.message : 'Unknown save error', is_recoverable: true, suggestions: ['Refresh the page','Try again later'], timestamp: new Date().toISOString(), severity: 'error' } }); }
  }, [activeConnectionId, jobs, updateJob, refetchStats, fetchPreviousBlogs]);

  const handleTaskError = useCallback(async (taskId: string, errorMessage: string) => {
    const errorInfo: ErrorInfo = { error_type: 'generation_error', user_message: errorMessage, technical_details: errorMessage, is_recoverable: true, suggestions: ['Try a different topic','Check your connection'], timestamp: new Date().toISOString(), severity: 'error' };
    updateJob(taskId, { status: 'failed', currentStep: 'Generation failed', progress: 0, error: errorInfo });
    if (activeConnectionId === taskId) {
      setActiveConnectionId(null);
      setIsGenerating(false); // Reset generating state on error
    }
    try { await blogService.updateBlogCompletion(taskId, 'failed', undefined, errorInfo); } catch (err) { console.error('Failed to persist error state:', err); }
  }, [activeConnectionId, updateJob]);

  const handleGenerateBlog = useCallback(async (topic: string, instructions: string) => {
    if (!topic.trim()) { setGenerationError('Please enter a topic'); return; }
    if (!canGenerate) { setGenerationError('Monthly generation limit reached. Upgrade to Premium for more.'); return; }
    if (activeConnectionId) { closeConnection(); setActiveConnectionId(null); }
    try {
      setGenerationError(null);
      setIsGenerating(true);
      setCreatingNew(false); // Once generation starts, exit new mode
      completedTasksRef.current.clear();
      firstUpdateReceivedRef.current = null; // Reset the flag for new generation
      const data = await blogService.generateBlog(topic.trim(), instructions.trim());
      createJob(data.task_id, topic.trim(), instructions.trim());
      setCurrentJobId(data.task_id);
      setActiveConnectionId(data.task_id);
      // Immediately refresh blog list to show the new blog card
      await fetchPreviousBlogs();
      try {
        await connectToTaskStream(
          data.task_id,
          (taskId: string, updates: Partial<JobState>) => {
            updateJob(taskId, updates);
            // Set isGenerating to false when we receive the first WebSocket update
            // This ensures the console stays visible until real-time updates start
            if (firstUpdateReceivedRef.current !== taskId) {
              firstUpdateReceivedRef.current = taskId;
              setIsGenerating(false);
            }
          },
          handleTaskCompletion,
          handleTaskError,
          (taskId: string, log: LogEntry) => setTaskLogs(prev => ({ ...prev, [taskId]: [...(prev[taskId] || []), log] }))
        );
        // Don't set isGenerating(false) here - let the first WebSocket update handle it
      } catch (wsErr) {
        console.error('Failed to start WebSocket stream:', wsErr);
        setGenerationError('Failed to establish real-time connection. Generation continues in background.');
        setIsGenerating(false);
      }
    } catch (err) {
      console.error('Error starting blog generation:', err);
      const msg = err instanceof Error ? err.message : 'Failed to start blog generation.';
      setGenerationError(msg);
      if (activeConnectionId) setActiveConnectionId(null);
      setIsGenerating(false);
    }
  }, [canGenerate, activeConnectionId, closeConnection, completedTasksRef, createJob, updateJob, connectToTaskStream, handleTaskCompletion, handleTaskError, fetchPreviousBlogs]);

  const handleJobClick = useCallback((jobId: string) => { if (activeConnectionId && activeConnectionId !== jobId) { closeConnection(); setActiveConnectionId(null); } setCurrentJobId(jobId); setGenerationError(null); }, [activeConnectionId, closeConnection]);
  const handleBlogClick = useCallback((blog: BlogData) => { setSelectedBlog(blog); setShowBlogModal(true); }, []);
  const handleDeleteBlog = useCallback((blogId: string) => { const blog = previousBlogs.find(b => b.id === blogId); if (blog) { setBlogToDelete(blog); setShowDeleteDialog(true); } }, [previousBlogs]);
  const handleBulkDeleteBlogs = useCallback(async (blogIds: string[]) => { try { const results = await Promise.all(blogIds.map(id => deleteBlog(id))); const succeeded = results.filter(Boolean).length; if (succeeded === blogIds.length) { await fetchPreviousBlogs(); } else { setGenerationError(`Failed to delete ${blogIds.length - succeeded} blog(s).`); } } catch (err) { console.error('Bulk delete failed:', err); setGenerationError('Bulk delete failed.'); } }, [deleteBlog, fetchPreviousBlogs]);
  const confirmDeleteBlog = useCallback(async () => { if (!blogToDelete) return; setIsDeleting(true); try { const success = await deleteBlog(blogToDelete.id); if (success) { setShowDeleteDialog(false); if (currentJobId === blogToDelete.id) { setCurrentJobId(null); setGenerationError(null); } } } catch (err) { console.error('Delete blog failed:', err); setGenerationError('Failed to delete blog.'); } finally { setIsDeleting(false); } }, [blogToDelete, deleteBlog, currentJobId]);
  const handleNewBlog = useCallback(() => {
    if (isGenerating && activeConnectionId) return; // prevent clearing active generation
    setCreatingNew(true);
    setCurrentJobId(null);
    setGenerationError(null);
    setSelectedBlog(null);
    setShowBlogModal(false);
  }, [isGenerating, activeConnectionId]);

  // State recovery: Check for active tasks on page load/refresh (run only once when authenticated)
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      const recoverActiveJobs = async () => {
        try {
          const activeTasks = await taskService.getActiveTasks();
          
          if (activeTasks.length > 0) {
            for (const task of activeTasks) {
              const job = taskService.convertTaskToJob(task);
              addTemporaryJob(job);
              
              // Auto-select the most recent in-progress task
              if (task.status === 'in_progress' && !currentJobId) {
                setCurrentJobId(task.id);
                setActiveConnectionId(task.id);
                
                // Reconnect WebSocket for in-progress tasks
                try {
                  await connectToTaskStream(
                    task.id,
                    (taskId: string, updates: Partial<JobState>) => updateJob(taskId, updates),
                    handleTaskCompletion,
                    handleTaskError,
                    (taskId: string, log: LogEntry) => setTaskLogs(prev => ({ ...prev, [taskId]: [...(prev[taskId] || []), log] }))
                  );
                } catch (wsErr) {
                  console.error(`Failed to reconnect to task ${task.id}:`, wsErr);
                  setGenerationError('Lost connection to active generation. Status may be outdated.');
                }
              }
            }
          }
        } catch (error) {
          console.error('Failed to recover active jobs:', error);
        }
      };
      
      recoverActiveJobs();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, isLoading]); // Only run when auth state changes, not on function changes

  return { isAuthenticated, isLoading, stats, statsLoading, isFree, jobs, previousBlogs, blogsLoading, currentJobId, currentJob, generationError, isGenerating, activeConnectionId, taskLogs, showDeleteDialog, blogToDelete, isDeleting, selectedBlog, showBlogModal, canGenerate, handleGenerateBlog, handleJobClick, handleBlogClick, handleDeleteBlog, handleBulkDeleteBlogs, confirmDeleteBlog, handleNewBlog, setShowDeleteDialog, setBlogToDelete, setIsDeleting, setGenerationError, setSelectedBlog, setShowBlogModal, refetchStats, fetchPreviousBlogs };
}
