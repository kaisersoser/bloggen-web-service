"use client"
import { useState, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { useAuth, useRoleCheck } from "@/hooks/useAuth";
import { useUserStats } from "@/hooks/useUserStats";
import { useBlogManagement } from "@/hooks/useBlogManagement";
import { useSSEConnection } from "@/hooks/useSSEConnection";
import { useInfiniteScroll } from "@/hooks/useInfiniteScroll";
import { DeleteConfirmationDialog } from "@/components/blog/DeleteConfirmationDialog";
import { UserProfile } from "@/components/auth/UserProfile";
import { JobDetailsModal } from "@/components/blog/JobDetailsModal";
import { BlogGenerationForm } from "@/components/blog/BlogGenerationForm";
import { JobsDashboard } from "@/components/blog/JobsDashboard";
import { PreviousBlogsSection } from "@/components/blog/PreviousBlogsSection";
import { signIn } from "next-auth/react";
import { blogService } from "@/lib/services/blog";
import { BlogData, ErrorInfo } from "@/types/blog";

export default function BlogGenerator() {
  const { isAuthenticated, isLoading } = useAuth();
  const { canGenerateBlog, isFree } = useRoleCheck();
  const { stats, loading: statsLoading, refetch: refetchStats } = useUserStats();
  
  const {
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
  } = useBlogManagement();

  const { connectToTaskStream, closeConnection, completedTasksRef } = useSSEConnection();
  
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [showJobDetails, setShowJobDetails] = useState(false);
  const [activeView, setActiveView] = useState<'form' | 'jobs' | 'details'>('form');
  const [generationError, setGenerationError] = useState<string | null>(null);
  
  // Delete confirmation dialog state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [blogToDelete, setBlogToDelete] = useState<BlogData | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // Infinite scroll hook for previous blogs
  const { displayedBlogs, hasMore, isLoading: scrollLoading } = useInfiniteScroll({
    allBlogs: previousBlogs,
    itemsPerPage: 6
  });

  // Memoized computed values
  const selectedJob = useMemo(() => 
    jobs.find(job => job.id === selectedJobId), 
    [jobs, selectedJobId]
  );

  const canGenerate = useMemo(() => 
    stats ? stats.remainingGenerations > 0 || stats.monthlyLimit === -1 : canGenerateBlog(),
    [stats, canGenerateBlog]
  );

  // Fetch previous blogs when user is authenticated
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      fetchPreviousBlogs();
    }
  }, [isAuthenticated, isLoading, fetchPreviousBlogs]);

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto p-4 space-y-4">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  // Show sign-in prompt if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto p-4 space-y-4">
        <div className="text-center py-12">
          <h1 className="text-3xl font-bold mb-4">AI Blog Generator</h1>
          <p className="text-gray-600 mb-8">Sign in to start generating amazing blogs with AI</p>
          <Button onClick={() => signIn()}>Sign In</Button>
        </div>
      </div>
    );
  }

  const handleGenerateBlog = async (topic: string, instructions: string) => {
    if (!topic.trim()) {
      setGenerationError('Please enter a topic');
      return;
    }

    if (!canGenerate) {
      setGenerationError('Monthly generation limit reached. Upgrade to Premium for unlimited access.');
      return;
    }

    try {
      setGenerationError(null);
      
      // Clear any previously completed tasks to allow new completions
      completedTasksRef.current.clear();
      
      const data = await blogService.generateBlog(topic, instructions);
      
      // Create new job and add to jobs list
      createJob(data.task_id, topic.trim(), instructions.trim());
      
      // Set this job as selected and show progress
      setSelectedJobId(data.task_id);
      setActiveView('details');
      setShowJobDetails(true);
      
      // Start SSE stream for real-time updates
      try {
        await connectToTaskStream(
          data.task_id,
          (taskId, updates) => {
            updateJob(taskId, updates);
            // Add log entry for status updates
            if (updates.currentStep) {
              addLogToJob(taskId, updates.currentStep, new Date().toISOString());
            }
          },
          handleTaskCompletion,
          handleTaskError
        );
      } catch (sseError) {
        console.error('Failed to start SSE stream:', sseError);
      }
      
    } catch (error) {
      console.error("Error starting blog generation:", error);
      setGenerationError(error instanceof Error ? error.message : 'Failed to start blog generation. Please try again.');
    }
  };

  const handleTaskCompletion = async (taskId: string, content: string) => {
    updateJob(taskId, {
      status: 'completed',
      currentStep: 'Blog generation complete!',
      progress: 100,
      blogContent: content,
      completedAt: new Date().toISOString()
    });
    
    try {
      await blogService.updateBlogCompletion(taskId, 'completed', content);
      refetchStats();
      fetchPreviousBlogs();
    } catch (error) {
      console.error('Failed to update blog completion status:', error);
    }
  };

  const handleTaskError = async (taskId: string, errorMessage: string) => {
    const errorInfo: ErrorInfo = {
      error_type: 'generation_error',
      user_message: errorMessage,
      technical_details: errorMessage,
      is_recoverable: false,
      suggestions: ['Please try again with a different topic'],
      timestamp: new Date().toISOString(),
      severity: 'error'
    };
    
    updateJob(taskId, {
      status: 'failed',
      currentStep: 'Generation failed',
      progress: 0,
      error: errorInfo
    });
    
    try {
      await blogService.updateBlogCompletion(taskId, 'failed', undefined, errorInfo);
    } catch (error) {
      console.error('Failed to update blog completion status:', error);
    }
  };

  const openJobDetails = (jobId: string) => {
    setSelectedJobId(jobId);
    setActiveView('details');
    setShowJobDetails(true);
  };

  const closeJobDetails = () => {
    setShowJobDetails(false);
    setSelectedJobId(null);
    closeConnection();
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
      }
    } finally {
      setIsDeleting(false);
    }
  };

  const openPreviousBlogDetails = (blog: BlogData) => {
    const jobState = convertBlogToJob(blog);
    addTemporaryJob(jobState);
    openJobDetails(blog.id);
  };

  return (
    <div className="max-w-6xl mx-auto p-4 space-y-4">
      {/* Header Navigation */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">AI Blog Generator</h1>
        <div className="flex space-x-2">
          <Button
            variant={activeView === 'form' ? 'default' : 'outline'}
            onClick={() => setActiveView('form')}
          >
            New Blog
          </Button>
          <Button
            variant={activeView === 'jobs' ? 'default' : 'outline'}
            onClick={() => setActiveView('jobs')}
          >
            Jobs ({jobs.length + previousBlogs.length})
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-3">
          {activeView === 'form' && (
            <>
              <BlogGenerationForm
                onGenerate={handleGenerateBlog}
                stats={stats}
                isFree={isFree}
                generationError={generationError}
                statsLoading={statsLoading}
              />
              
              <PreviousBlogsSection
                blogs={displayedBlogs}
                loading={blogsLoading}
                hasMore={hasMore}
                scrollLoading={scrollLoading}
                onBlogClick={openPreviousBlogDetails}
                onDeleteBlog={handleDeleteBlog}
              />
            </>
          )}

          {activeView === 'jobs' && (
            <JobsDashboard
              jobs={jobs}
              previousBlogs={displayedBlogs}
              blogsLoading={blogsLoading}
              hasMore={hasMore}
              scrollLoading={scrollLoading}
              onJobClick={openJobDetails}
              onBlogClick={openPreviousBlogDetails}
              onDeleteJob={deleteJob}
              onDeleteBlog={handleDeleteBlog}
            />
          )}
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-1">
          <UserProfile />
        </div>
      </div>

      {/* Job Details Modal */}
      {showJobDetails && selectedJobId && selectedJob && (
        <JobDetailsModal
          job={selectedJob}
          onClose={closeJobDetails}
        />
      )}

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
    </div>
  );
}
