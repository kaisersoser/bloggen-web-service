"use client"
import { useState } from "react";
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import { UserProfileDropdown } from "@/components/auth/UserProfileDropdown";
import { TabbedPromptInterface } from "@/components/blog/TabbedPromptInterface";
import { BlogTileGrid } from "@/components/blog/BlogTileGrid";
import { GenerationLogModal } from "@/components/blog/GenerationLogModal";
import { DraftPreviewModal } from "@/components/blog/DraftPreviewModal";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { useTheme } from "@/components/theme/ThemeProvider";
import { useBlogGenerator } from "@/hooks/useBlogGenerator";
import { useGenerationLogs } from "@/hooks/useGenerationLogs";
import { useDraftContent } from "@/hooks/useDraftContent";
import { signIn } from "next-auth/react";
import { logger } from "@/lib/logger";
import { blogService } from "@/lib/services/blog";

const DeleteConfirmationDialog = dynamic(
  () => import("@/components/blog/DeleteConfirmationDialog").then((mod) => mod.DeleteConfirmationDialog),
  { loading: () => null }
);

const BlogViewModal = dynamic(
  () => import("@/components/blog/BlogViewModal").then((mod) => mod.BlogViewModal),
  { ssr: false, loading: () => null }
);

export default function BlogGenerator() {
  const { theme, setTheme } = useTheme();
  
  // Queue modal states
  const [showLogsModal, setShowLogsModal] = useState(false);
  const [showDraftModal, setShowDraftModal] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  
  const {
    isAuthenticated,
    isLoading,
    stats,
    jobs,
    previousBlogs,
    blogsLoading,
    generationError,
    isGenerating,
    showDeleteDialog,
    blogToDelete,
    isDeleting,
    selectedBlog,
    showBlogModal,
    taskLogs,
    currentJobId,
    currentJob,
    handleGenerateBlog,
    handleBlogClick,
    handleBulkDeleteBlogs,
    confirmDeleteBlog,
    clearTaskLogs,
    setBlogToDelete,
    setIsDeleting,
    setSelectedBlog,
    setShowBlogModal,
    setShowDeleteDialog,
    setGenerationError
  } = useBlogGenerator();
  
  // Determine if a blog is actively generating (for live log updates)
  // MUST be defined AFTER previousBlogs is available
  const isLiveGeneration = (taskId: string | null) => {
    if (!taskId) return false;
    const blog = previousBlogs?.find(b => b.id === taskId);
    return blog?.status === 'in_progress' || blog?.status === 'IN_PROGRESS';
  };
  
  // Fetch logs for selected task - disable polling if task is live (SSE will handle it)
  const shouldPollLogs = selectedTaskId ? !isLiveGeneration(selectedTaskId) : false;
  const { logs, isLoading: logsLoading, refresh: refreshLogs } = useGenerationLogs(
    selectedTaskId,
    showLogsModal && selectedTaskId !== null && shouldPollLogs,
    2000
  );
  
  const { draft, isLoading: draftLoading, refresh: refreshDraft } = useDraftContent(
    selectedTaskId,
    showDraftModal && selectedTaskId !== null,
    3000
  );
  
  // Queue action handlers
  const handleViewLogs = (taskId: string) => {
    setSelectedTaskId(taskId);
    setShowLogsModal(true);
  };
  
  const handleViewDraft = (taskId: string) => {
    setSelectedTaskId(taskId);
    setShowDraftModal(true);
  };
  
  const handleRetry = async (blogId: string) => {
    try {
      await blogService.retryBlog(blogId);
      // Blog list will refresh automatically
    } catch (error: any) {
      setGenerationError(error.message || 'Failed to retry blog generation');
    }
  };

  // Debug logging
  logger.debug('Blog page render debug', {
    jobsCount: jobs?.length || 0,
    previousBlogsCount: previousBlogs?.length || 0,
    jobsData: jobs?.map(j => ({ id: j.id, topic: j.topic, status: j.status })) || [],
    previousBlogsData: previousBlogs?.map(b => ({ 
      id: b.id, 
      topic: b.topic, 
      status: b.status,
      hasContent: !!b.content, 
      hasHeroImage: !!b.heroImageUrl 
    })) || []
  });

  const activeConnectionStatus = currentJob?.connectionState ? {
    status: currentJob.connectionState,
    message: currentJob.connectionMessage,
    updatedAt: currentJob.connectionUpdatedAt,
  } : null;

  // Loading state while authenticating
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

  // Unauthenticated prompt
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* Fixed Header */}
      <div className="sticky top-0 z-40 bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl">
              <span className="text-white text-lg font-bold">AI</span>
            </div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white">Blog Generator</h1>
          </div>
          <div className="flex items-center gap-4">
            <UserProfileDropdown themeMode={theme} onThemeChange={setTheme} />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Tabbed Prompt Interface */}
        <div className="flex justify-center">
          <TabbedPromptInterface
            onSubmit={(prompt: string) => handleGenerateBlog(prompt, '')}
            isGenerating={isGenerating}
            disabled={false}
            remainingGenerations={stats?.remainingGenerations}
            userRole={stats?.role as 'FREE' | 'PREMIUM' | 'ADMIN'}
            taskLogs={taskLogs}
            currentJobId={currentJobId}
            clearTaskLogs={clearTaskLogs}
            connectionStatus={activeConnectionStatus}
          />
        </div>

        {/* Error Display */}
        {generationError && (
          <div className="max-w-4xl mx-auto">
            <ErrorBanner
              message={generationError}
              onClose={() => setGenerationError(null)}
            />
          </div>
        )}

        {/* Blog Tile Grid - Keep original layout */}
        <div>
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              Your Blog Collection
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Browse and manage your AI-generated blog posts
            </p>
          </div>
          
          <BlogTileGrid
            blogs={previousBlogs || []}
            onBlogView={handleBlogClick}
            onBlogDelete={(blog) => {
              setBlogToDelete(blog);
              setShowDeleteDialog(true);
            }}
            onBulkDeleteBlogs={handleBulkDeleteBlogs}
            isLoading={blogsLoading}
            onViewLogs={handleViewLogs}
            onViewDraft={handleViewDraft}
            onRetry={handleRetry}
          />
        </div>
      </div>

      {/* Modals */}
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

      <BlogViewModal
        blog={selectedBlog}
        isOpen={showBlogModal}
        onClose={() => {
          setShowBlogModal(false);
          setSelectedBlog(null);
        }}
      />
      
      {/* Generation Log Modal - Opens when user clicks "View Logs" */}
      <GenerationLogModal
        isOpen={showLogsModal}
        onClose={() => {
          setShowLogsModal(false);
          setSelectedTaskId(null);
        }}
        taskId={selectedTaskId || ''}
        logs={(() => {
          const isLive = selectedTaskId ? isLiveGeneration(selectedTaskId) : false;
          const logsToUse = isLive && selectedTaskId && taskLogs[selectedTaskId] 
            ? taskLogs[selectedTaskId] 
            : logs;
          console.log('[LOG MODAL DEBUG]', {
            selectedTaskId,
            isLive,
            taskLogsForTask: selectedTaskId ? taskLogs[selectedTaskId]?.length : 0,
            httpLogsCount: logs.length,
            logsToUseCount: logsToUse.length,
            allTaskLogKeys: Object.keys(taskLogs),
            firstLog: logsToUse[0]
          });
          return logsToUse.map(log => ({
            timestamp: log.timestamp,
            step: log.step,
            message: log.message,
            progress: log.progress,
            level: (log.level as 'info' | 'warning' | 'error' | 'success') || 'info'
          }));
        })()}
        isLoading={logsLoading}
        isLive={selectedTaskId ? isLiveGeneration(selectedTaskId) : false}
        onRefresh={refreshLogs}
      />
      
      {/* Draft Preview Modal - Opens when user clicks "View Draft" */}
      <DraftPreviewModal
        isOpen={showDraftModal}
        onClose={() => {
          setShowDraftModal(false);
          setSelectedTaskId(null);
        }}
        taskId={selectedTaskId || ''}
        draft={draft}
        isLoading={draftLoading}
        onRefresh={refreshDraft}
      />
    </div>
  );
}
