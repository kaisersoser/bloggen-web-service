import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useAuth, useRoleCheck } from '@/hooks/useAuth';
import { useUserStats } from '@/hooks/useUserStats';
import { useBlogManagement } from '@/hooks/useBlogManagement';
import { useEnhancedSSEConnection } from '@/hooks/useEnhancedSSE';
import { useAuthenticationErrorHandler } from '@/hooks/useAuthenticationErrorHandler';
import { blogService } from '@/lib/services/blog';
import { taskService } from '@/lib/services/task';
import { BlogData, ErrorInfo, LogEntry, JobState } from '@/types/blog';
// PromptConfig import removed (unused after refactor)

export function useBlogGenerator() {
  const { isAuthenticated, isLoading } = useAuth();
  const { canGenerateBlog, isFree } = useRoleCheck();
  const { stats, loading: statsLoading, refetch: refetchStats } = useUserStats();
  const { jobs, previousBlogs, blogsLoading, updateJob, createJob, fetchPreviousBlogs, deleteBlog, deleteTask, deleteJob, addTemporaryJob } = useBlogManagement();
  const { connectToTaskStream, closeConnection, completedTasksRef } = useEnhancedSSEConnection();
  const { handleAuthError } = useAuthenticationErrorHandler();

  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeConnectionId, setActiveConnectionId] = useState<string | null>(null);
  const [taskLogs, setTaskLogs] = useState<Record<string, LogEntry[]>>({});
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [blogToDelete, setBlogToDelete] = useState<BlogData | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // Track if we've received the first SSE update to avoid multiple setIsGenerating(false) calls
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
  
  // Safety mechanism: Reset generating state when an error occurs
  useEffect(() => {
    if (generationError && isGenerating) {
      console.log('🔧 Safety reset: Setting isGenerating(false) due to generation error');
      setIsGenerating(false);
    }
  }, [generationError, isGenerating]);

  const handleTaskCompletion = useCallback(async (taskId: string, content: string, heroImageUrl?: string) => {
    console.log('🔍 Frontend handleTaskCompletion called:', {
      taskId,
      contentLength: content?.length || 0,
      hasContent: !!content,
      contentPreview: content?.substring(0, 100) + '...',
      heroImageUrl,
      currentJobsCount: jobs.length,
      currentPreviousBlogsCount: previousBlogs.length
    });
    
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
    
    // CRITICAL FIX: Remove duplicate completion persistence call
    // The backend already handles completion persistence in task_manager.complete_task()
    // This was causing duplicate API calls and "Invalid status" errors
    console.log('✅ Blog completion handled locally - backend already persisted completion');
    
    // CRITICAL: Remove completed job from local jobs array FIRST to prevent duplicates
    console.log('🗑️ Removing job from local state:', taskId);
    console.log('📊 Jobs before deletion:', jobs.map(j => ({ id: j.id, topic: j.topic, status: j.status })));
    deleteJob(taskId);
    console.log('✅ Removed completed job from local state to prevent duplicate cards');
    
    // Refresh data without making duplicate completion API call
    try { 
      console.log('🔄 Refreshing stats and blog list...');
      await Promise.all([refetchStats(), fetchPreviousBlogs()]); 
      console.log('✅ Refreshed stats and blog list after completion');
      console.log('📊 Previous blogs after refresh:', previousBlogs.map(b => ({ id: b.id, topic: b.topic, status: b.status })));
    }
    catch (err) { 
      console.error('Failed to refresh data after completion:', err);
      // Don't mark as failed since completion itself succeeded
    }
  }, [activeConnectionId, jobs, previousBlogs, updateJob, refetchStats, fetchPreviousBlogs, deleteJob]);

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
    console.log('🚀 handleGenerateBlog called with:', { topic, instructions, canGenerate, activeConnectionId });
    
    if (!topic.trim()) { 
      console.log('❌ Empty topic provided');
      setGenerationError('Please enter a topic'); 
      return; 
    }
    if (!canGenerate) { 
      console.log('❌ Cannot generate - limit reached');
      setGenerationError('Monthly generation limit reached. Upgrade to Premium for more.'); 
      return; 
    }
    if (activeConnectionId) { 
      console.log('🔄 Closing existing connection:', activeConnectionId);
      closeConnection(); 
      setActiveConnectionId(null); 
    }
    
    try {
      console.log('🎯 Starting blog generation process...');
      setGenerationError(null);
      setIsGenerating(true);
      setCreatingNew(false); // Once generation starts, exit new mode
      completedTasksRef.current.clear();
      firstUpdateReceivedRef.current = null; // Reset the flag for new generation
      
      // Don't clear taskLogs here - let the console handle it when user submits
      // This prevents interference with SSE message flow
      
      // SOLUTION: Pre-generate task ID and start generation BEFORE establishing SSE connection
      console.log('🆔 Pre-generating task ID for blog generation...');
      const taskId = await blogService.generateTaskId();
      console.log('🆔 Generated task ID:', taskId);
      
      // Create job and set current state immediately
      console.log('📝 Creating local job for task:', taskId);
      createJob(taskId, topic.trim(), instructions.trim());
      setCurrentJobId(taskId);
      setActiveConnectionId(taskId);
      console.log('✅ Local job created and state updated');
      
      // FIXED: Start blog generation FIRST to ensure backend task exists
      console.log('🚀 Starting blog generation to create backend task...');
      const data = await blogService.generateBlog(topic.trim(), instructions.trim(), taskId);
      console.log('✅ Blog generation started with task ID:', data.task_id);
      
      // Verify the task IDs match
      if (data.task_id !== taskId) {
        console.warn('⚠️ Task ID mismatch! Expected:', taskId, 'Got:', data.task_id);
      }
      
      // NOW establish SSE connection to the existing backend task
      console.log('🔗 Establishing SSE connection to existing backend task:', taskId);
      try {
        await connectToTaskStream(
          taskId,
          (taskId: string, updates: Partial<JobState>) => {
            console.log('🔄 useBlogGenerator: SSE Update received:', taskId, updates);
            updateJob(taskId, updates);
            // Keep isGenerating true until actual completion
            // Only track that we received the first update for debugging
            if (firstUpdateReceivedRef.current !== taskId) {
              firstUpdateReceivedRef.current = taskId;
              console.log('✅ First SSE update received, real-time connection active');
            }
          },
          (taskId: string, content: string, heroImageUrl?: string) => {
            // Only set isGenerating to false when task actually completes
            console.log('🎉 Blog generation completed, setting isGenerating to false');
            setIsGenerating(false);
            handleTaskCompletion(taskId, content, heroImageUrl);
          },
          handleTaskError,
          (taskId: string, log: LogEntry) => setTaskLogs(prev => ({ ...prev, [taskId]: [...(prev[taskId] || []), log] }))
        );
        console.log('✅ SSE connection established successfully to existing task:', taskId);
        
        // Don't set isGenerating(false) here - let the first SSE update handle it
      } catch (sseErr) {
        console.error('Failed to start SSE stream:', sseErr);
        
        // Handle authentication errors in SSE connection
        if (sseErr instanceof Error) {
          const wasAuthError = handleAuthError(sseErr);
          if (wasAuthError) {
            setIsGenerating(false);
            return;
          }
        }
        
        setGenerationError('Real-time updates unavailable, but your blog is being generated in the background. Refresh the page in a few minutes to see your completed blog.');
        setIsGenerating(false);
      }
    } catch (err) {
      console.error('Error starting blog generation:', err);
      
      // Handle authentication errors specially
      if (err instanceof Error) {
        const wasAuthError = handleAuthError(err);
        if (wasAuthError) {
          setIsGenerating(false);
          return; // Don't show generic error if we handled auth error
        }
      }
      
      const msg = err instanceof Error ? err.message : 'Failed to start blog generation.';
      setGenerationError(msg);
      if (activeConnectionId) setActiveConnectionId(null);
      setIsGenerating(false);
    }
  }, [canGenerate, activeConnectionId, closeConnection, completedTasksRef, createJob, updateJob, connectToTaskStream, handleTaskCompletion, handleTaskError, handleAuthError]);

  const handleJobClick = useCallback((jobId: string) => { 
    if (activeConnectionId && activeConnectionId !== jobId) { 
      closeConnection(); 
      setActiveConnectionId(null); 
    } 
    setCurrentJobId(jobId); 
    setGenerationError(null); 
  }, [activeConnectionId, closeConnection]);
  const handleBlogClick = useCallback((blog: BlogData) => { 
    setSelectedBlog(blog); 
    setShowBlogModal(true); 
  }, []);
  const handleDeleteBlog = useCallback((blogId: string) => { 
    const blog = previousBlogs.find(b => b.id === blogId); 
    if (blog) { 
      setBlogToDelete(blog); 
      setShowDeleteDialog(true); 
    } 
  }, [previousBlogs]);
  const handleBulkDeleteBlogs = useCallback(async (blogIds: string[]) => { 
    try { 
      const results = await Promise.all(blogIds.map(id => deleteBlog(id))); 
      const succeeded = results.filter(Boolean).length; 
      if (succeeded === blogIds.length) { 
        await fetchPreviousBlogs(); 
      } else { 
        setGenerationError(`Failed to delete ${blogIds.length - succeeded} blog(s).`); 
      } 
    } catch (err) { 
      console.error('Bulk delete failed:', err); 
      setGenerationError('Bulk delete failed.'); 
    } 
  }, [deleteBlog, fetchPreviousBlogs]);
  const handleDeleteStuckTask = useCallback(async (taskId: string) => { 
    try { 
      await deleteTask(taskId); 
      // If we reach here, deletion was successful
      if (currentJobId === taskId) { 
        setCurrentJobId(null); 
        setGenerationError(null); 
      } 
      if (activeConnectionId === taskId) { 
        closeConnection(); 
        setActiveConnectionId(null); 
      } 
      await fetchPreviousBlogs(); 
    } catch (err) { 
      console.error('Delete stuck task failed:', err); 
      setGenerationError('Failed to delete stuck task.'); 
    } 
  }, [deleteTask, currentJobId, activeConnectionId, closeConnection, fetchPreviousBlogs]);
  const confirmDeleteBlog = useCallback(async () => { if (!blogToDelete) return; setIsDeleting(true); try { const success = await deleteBlog(blogToDelete.id); if (success) { setShowDeleteDialog(false); if (currentJobId === blogToDelete.id) { setCurrentJobId(null); setGenerationError(null); } } } catch (err) { console.error('Delete blog failed:', err); setGenerationError('Failed to delete blog.'); } finally { setIsDeleting(false); } }, [blogToDelete, deleteBlog, currentJobId]);
  const handleNewBlog = useCallback(() => {
    if (isGenerating && activeConnectionId) return; // prevent clearing active generation
    setCreatingNew(true);
    setCurrentJobId(null);
    setGenerationError(null);
    setSelectedBlog(null);
    setShowBlogModal(false);
  }, [isGenerating, activeConnectionId]);

  // Function to clear taskLogs (used by TabbedPromptInterface)
  const clearTaskLogs = useCallback(() => {
    setTaskLogs({});
    console.log('🧹 TaskLogs cleared via clearTaskLogs callback');
  }, []);

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
                
                // Reconnect SSE for in-progress tasks
                try {
                  await connectToTaskStream(
                    task.id,
                    (taskId: string, updates: Partial<JobState>) => updateJob(taskId, updates),
                    handleTaskCompletion,
                    handleTaskError,
                    (taskId: string, log: LogEntry) => setTaskLogs(prev => ({ ...prev, [taskId]: [...(prev[taskId] || []), log] }))
                  );
                } catch (sseErr) {
                  console.error(`Failed to reconnect to task ${task.id}:`, sseErr);
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

  return { isAuthenticated, isLoading, stats, statsLoading, isFree, jobs, previousBlogs, blogsLoading, currentJobId, currentJob, generationError, isGenerating, activeConnectionId, taskLogs, showDeleteDialog, blogToDelete, isDeleting, selectedBlog, showBlogModal, canGenerate, handleGenerateBlog, handleJobClick, handleBlogClick, handleDeleteBlog, handleBulkDeleteBlogs, handleDeleteStuckTask, confirmDeleteBlog, handleNewBlog, clearTaskLogs, setShowDeleteDialog, setBlogToDelete, setIsDeleting, setGenerationError, setSelectedBlog, setShowBlogModal, refetchStats, fetchPreviousBlogs };
}
