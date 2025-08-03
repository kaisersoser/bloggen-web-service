"use client"
import { useState, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { useAuth, useRoleCheck } from "@/hooks/useAuth";
import { useUserStats } from "@/hooks/useUserStats";
import { useBlogManagement } from "@/hooks/useBlogManagement";
import { useSSEConnection } from "@/hooks/useSSEConnection";
import { DeleteConfirmationDialog } from "@/components/blog/DeleteConfirmationDialog";
import { UserProfileDropdown } from "@/components/auth/UserProfileDropdown";
import { ChatPromptInput } from "@/components/blog/ChatPromptInput";
import { BlogGenerationView } from "@/components/blog/BlogGenerationView";
import { BlogHistorySidebar } from "@/components/blog/BlogHistorySidebar";
import { BlogViewModal } from "@/components/blog/BlogViewModal";
import { useTheme } from "@/components/theme/ThemeProvider";
import { signIn } from "next-auth/react";
import { blogService } from "@/lib/services/blog";
import { BlogData, ErrorInfo, LogEntry } from "@/types/blog";

export default function BlogGenerator() {
  const { isAuthenticated, isLoading } = useAuth();
  const { canGenerateBlog, isFree } = useRoleCheck();
  const { stats, loading: statsLoading, refetch: refetchStats } = useUserStats();
  const { theme, setTheme } = useTheme();
  
  const {
    jobs,
    previousBlogs,
    blogsLoading,
    updateJob,
    createJob,
    deleteJob,
    fetchPreviousBlogs,
    deleteBlog
  } = useBlogManagement();

  const { connectToTaskStream, closeConnection, completedTasksRef } = useSSEConnection();
  
  // UI State
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activeConnectionId, setActiveConnectionId] = useState<string | null>(null);
  const [taskLogs, setTaskLogs] = useState<Record<string, LogEntry[]>>({});
  
  // Delete confirmation dialog state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [blogToDelete, setBlogToDelete] = useState<BlogData | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Blog view modal state
  const [selectedBlog, setSelectedBlog] = useState<BlogData | null>(null);
  const [showBlogModal, setShowBlogModal] = useState(false);

  // Cleanup SSE connections on unmount or job change
  useEffect(() => {
    return () => {
      if (activeConnectionId) {
        closeConnection();
        setActiveConnectionId(null);
      }
    };
  }, [activeConnectionId, closeConnection]);

  // Clear errors when switching jobs
  useEffect(() => {
    setGenerationError(null);
  }, [currentJobId]);

  // Memoized computed values with proper null checking
  const currentJob = useMemo(() => {
    if (!currentJobId) return null;
    return jobs.find(job => job.id === currentJobId) || null;
  }, [jobs, currentJobId]);

  const canGenerate = useMemo(() => {
    if (!stats) return canGenerateBlog();
    return stats.remainingGenerations > 0 || stats.monthlyLimit === -1;
  }, [stats, canGenerateBlog]);

  // Fetch previous blogs when user is authenticated
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      fetchPreviousBlogs();
    }
  }, [isAuthenticated, isLoading, fetchPreviousBlogs]);

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="animate-pulse text-center">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-64 mb-4 mx-auto"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-48 mx-auto"></div>
        </div>
      </div>
    );
  }

  // Show sign-in prompt if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-3xl font-bold mb-4 text-gray-900 dark:text-gray-100">AI Blog Generator</h1>
          <p className="text-gray-600 dark:text-gray-400 mb-8">Sign in to start generating amazing blogs with AI</p>
          <Button onClick={() => signIn()}>Sign In</Button>
        </div>
      </div>
    );
  }

  const handleGenerateBlog = async (topic: string, instructions: string) => {
    // Input validation
    if (!topic.trim()) {
      setGenerationError('Please enter a topic');
      return;
    }

    if (!canGenerate) {
      setGenerationError('Monthly generation limit reached. Upgrade to Premium for unlimited access.');
      return;
    }

    // Close any existing connections before starting new one
    if (activeConnectionId) {
      closeConnection();
      setActiveConnectionId(null);
    }

    try {
      setGenerationError(null);
      setIsGenerating(true);
      
      // Clear any previously completed tasks to allow new completions
      completedTasksRef.current.clear();
      
      const data = await blogService.generateBlog(topic.trim(), instructions.trim());
      
      // Create new job and add to jobs list
      createJob(data.task_id, topic.trim(), instructions.trim());
      
      // Set this job as current
      setCurrentJobId(data.task_id);
      setActiveConnectionId(data.task_id);
      
      // Start SSE stream for real-time updates
      try {
        await connectToTaskStream(
          data.task_id,
          (taskId, updates) => {
            updateJob(taskId, updates);
          },
          handleTaskCompletion,
          handleTaskError,
          (taskId, log) => {
            // Add log entry to task logs
            setTaskLogs(prev => ({
              ...prev,
              [taskId]: [...(prev[taskId] || []), log]
            }));
          }
        );
      } catch (sseError) {
        console.error('Failed to start SSE stream:', sseError);
        setGenerationError('Failed to establish real-time connection. The blog is still being generated.');
      }
      
    } catch (error) {
      console.error("Error starting blog generation:", error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to start blog generation. Please try again.';
      setGenerationError(errorMessage);
      
      // Clean up if job creation failed
      if (activeConnectionId) {
        setActiveConnectionId(null);
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleTaskCompletion = async (taskId: string, content: string) => {
    // Optimistically update local state
    updateJob(taskId, {
      status: 'completed',
      currentStep: 'Blog generation complete!',
      progress: 100,
      blogContent: content,
      completedAt: new Date().toISOString()
    });
    
    // Clean up connection
    if (activeConnectionId === taskId) {
      setActiveConnectionId(null);
    }
    
    // Convert completed job to BlogData format for modal display
    const currentJobData = jobs.find(job => job.id === taskId);
    if (currentJobData) {
      const blogData: BlogData = {
        id: taskId,
        userId: '', // Not needed for modal display
        topic: currentJobData.topic,
        instructions: currentJobData.instructions,
        content: content,
        status: 'completed',
        progress: 100,
        currentStep: 'Blog generation complete!',
        error: null,
        createdAt: new Date(currentJobData.createdAt),
        updatedAt: new Date(),
        completedAt: new Date()
      };
      
      // Show the completed blog in modal
      setSelectedBlog(blogData);
      setShowBlogModal(true);
    }
    
    // Persist to server
    try {
      await blogService.updateBlogCompletion(taskId, 'completed', content);
      // Refresh stats and blogs in parallel for better UX
      await Promise.all([
        refetchStats(),
        fetchPreviousBlogs()
      ]);
    } catch (error) {
      console.error('Failed to update blog completion status:', error);
      // Revert optimistic update on failure
      updateJob(taskId, {
        status: 'failed',
        currentStep: 'Failed to save blog',
        error: {
          error_type: 'save_error',
          user_message: 'Blog generated successfully but failed to save. Please try again.',
          technical_details: error instanceof Error ? error.message : 'Unknown save error',
          is_recoverable: true,
          suggestions: ['Try refreshing the page', 'Contact support if the problem persists'],
          timestamp: new Date().toISOString(),
          severity: 'error'
        }
      });
    }
  };

  const handleTaskError = async (taskId: string, errorMessage: string) => {
    const errorInfo: ErrorInfo = {
      error_type: 'generation_error',
      user_message: errorMessage,
      technical_details: errorMessage,
      is_recoverable: true,
      suggestions: ['Please try again with a different topic', 'Check your internet connection', 'Contact support if the problem persists'],
      timestamp: new Date().toISOString(),
      severity: 'error'
    };
    
    // Update local state
    updateJob(taskId, {
      status: 'failed',
      currentStep: 'Generation failed',
      progress: 0,
      error: errorInfo
    });
    
    // Clean up connection
    if (activeConnectionId === taskId) {
      setActiveConnectionId(null);
    }
    
    // Persist error state to server
    try {
      await blogService.updateBlogCompletion(taskId, 'failed', undefined, errorInfo);
    } catch (error) {
      console.error('Failed to update blog error status:', error);
      // This is a secondary error, log but don't update UI again
    }
  };

  const handleJobClick = (jobId: string) => {
    // Clear any existing connections before switching
    if (activeConnectionId && activeConnectionId !== jobId) {
      closeConnection();
      setActiveConnectionId(null);
    }
    
    setCurrentJobId(jobId);
    setGenerationError(null); // Clear errors when switching jobs
  };

  const handleBlogClick = (blog: BlogData) => {
    // Show the blog in modal instead of converting to job
    setSelectedBlog(blog);
    setShowBlogModal(true);
  };

  const handleDeleteCurrentItem = async () => {
    if (!currentJobId || !currentJob) return;
    
    // Close connection if deleting active job
    if (activeConnectionId === currentJobId) {
      closeConnection();
      setActiveConnectionId(null);
    }
    
    try {
      if (currentJob.status === 'completed') {
        // Delete from server (this is a saved blog)
        await deleteBlog(currentJobId);
      } else {
        // Just remove from local jobs list (this is an active job)
        deleteJob(currentJobId);
      }
      
      // Clear current view
      setCurrentJobId(null);
      setGenerationError(null);
    } catch (error) {
      console.error('Failed to delete item:', error);
      setGenerationError('Failed to delete. Please try again.');
    }
  };

  const handleDeleteBlog = (blogId: string) => {
    const blog = previousBlogs.find(b => b.id === blogId);
    if (blog) {
      setBlogToDelete(blog);
      setShowDeleteDialog(true);
    }
  };

  const confirmDeleteBlog = async () => {
    if (!blogToDelete) return;

    try {
      setIsDeleting(true);
      const success = await deleteBlog(blogToDelete.id);
      if (success) {
        setShowDeleteDialog(false);
        setBlogToDelete(null);
        // If we deleted the currently viewed blog, clear the view
        if (currentJobId === blogToDelete.id) {
          setCurrentJobId(null);
          setGenerationError(null);
        }
      }
    } catch (error) {
      console.error('Failed to delete blog:', error);
      setGenerationError('Failed to delete blog. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleNewBlog = () => {
    // Close any active connections
    if (activeConnectionId) {
      closeConnection();
      setActiveConnectionId(null);
    }
    
    // Clear all state for fresh start
    setCurrentJobId(null);
    setGenerationError(null);
    setIsGenerating(false);
  };

  return (
    <div className="h-screen bg-gray-50 dark:bg-gray-900 flex">
      {/* Sidebar */}
      <BlogHistorySidebar
        blogs={previousBlogs}
        jobs={jobs}
        loading={blogsLoading}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        onBlogClick={handleBlogClick}
        onJobClick={handleJobClick}
        onDeleteBlog={handleDeleteBlog}
        onNewBlog={handleNewBlog}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">AI Blog Generator</h1>
          <UserProfileDropdown themeMode={theme} onThemeChange={setTheme} />
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col">
          {currentJobId && currentJob ? (
            <>
              <BlogGenerationView
                job={currentJob}
                isGenerating={isGenerating || currentJob.status === 'in_progress'}
                logs={currentJobId ? taskLogs[currentJobId] || [] : []}
              />
              
              {/* Action buttons for completed blogs */}
              {currentJob.status === 'completed' && (
                <div className="border-t border-gray-200 bg-white p-4">
                  <div className="max-w-4xl mx-auto flex justify-between items-center">
                    <Button
                      variant="outline"
                      onClick={handleNewBlog}
                      disabled={isDeleting}
                    >
                      New Blog
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={handleDeleteCurrentItem}
                      disabled={isDeleting}
                    >
                      {isDeleting ? 'Deleting...' : (currentJob.status === 'completed' ? 'Delete Blog' : 'Cancel Generation')}
                    </Button>
                  </div>
                </div>
              )}
              
              {/* Error Display for Current Job */}
              {generationError && (
                <div className="border-t border-red-200 bg-red-50 p-4">
                  <div className="max-w-4xl mx-auto">
                    <div className="flex items-center">
                      <div className="flex-shrink-0">
                        <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div className="ml-3">
                        <p className="text-sm text-red-800">{generationError}</p>
                      </div>
                      <div className="ml-auto pl-3">
                        <button
                          onClick={() => setGenerationError(null)}
                          className="inline-flex bg-red-50 rounded-md p-1.5 text-red-500 hover:bg-red-100 focus:outline-none"
                        >
                          <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex-1 flex flex-col">
              {/* Welcome Message */}
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center max-w-md">
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
                    Welcome to AI Blog Generator
                  </h2>
                  <p className="text-gray-600 dark:text-gray-400 mb-8">
                    Create engaging, well-researched blog posts with the power of AI. 
                    Our CrewAI-powered system researches, writes, and fact-checks your content automatically.
                  </p>
                  <div className="grid grid-cols-3 gap-4 text-sm text-gray-500 dark:text-gray-400">
                    <div>🔍 Research</div>
                    <div>✍️ Generate</div>
                    <div>✅ Verify</div>
                  </div>
                </div>
              </div>

              {/* Input Area */}
              <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
                <div className="max-w-4xl mx-auto p-6">
                  <ChatPromptInput
                    onGenerate={handleGenerateBlog}
                    stats={stats}
                    isFree={isFree}
                    generationError={generationError}
                    statsLoading={statsLoading}
                    isGenerating={isGenerating}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        isOpen={showDeleteDialog}
        onClose={() => {
          setShowDeleteDialog(false);
          setBlogToDelete(null);
          setIsDeleting(false);
        }}
        onConfirm={confirmDeleteBlog}
        blogTopic={blogToDelete?.topic || ''}
        isDeleting={isDeleting}
      />

      {/* Blog View Modal */}
      <BlogViewModal
        blog={selectedBlog}
        isOpen={showBlogModal}
        onClose={() => {
          setShowBlogModal(false);
          setSelectedBlog(null);
        }}
      />
    </div>
  );
}
