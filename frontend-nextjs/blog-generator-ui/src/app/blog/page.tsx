"use client"
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { UserProfileDropdown } from "@/components/auth/UserProfileDropdown";
import { ChatPromptInput } from "@/components/blog/ChatPromptInput";
import { BlogGenerationView } from "@/components/blog/BlogGenerationView";
import { BlogHistorySidebar } from "@/components/blog/BlogHistorySidebar";
import { BlogViewModal } from "@/components/blog/BlogViewModal";
import { DeleteConfirmationDialog } from "@/components/blog/DeleteConfirmationDialog";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { useTheme } from "@/components/theme/ThemeProvider";
import { useBlogGenerator } from "@/hooks/useBlogGenerator";
import { signIn } from "next-auth/react";

export default function BlogGenerator() {
  const { theme, setTheme } = useTheme();
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const {
    isAuthenticated,
    isLoading,
    stats,
    statsLoading,
    isFree,
    jobs,
    previousBlogs,
    blogsLoading,
    currentJobId,
    currentJob,
    generationError,
    isGenerating,
    taskLogs,
    showDeleteDialog,
    blogToDelete,
    isDeleting,
    selectedBlog,
    showBlogModal,
    handleGenerateBlog,
    handleJobClick,
    handleBlogClick,
    handleDeleteBlog,
    handleBulkDeleteBlogs,
    confirmDeleteBlog,
    handleNewBlog,
  // handleDeleteCurrentItem removed (Delete action bar button deprecated)
    setShowDeleteDialog,
    setBlogToDelete,
    setIsDeleting,
    setGenerationError,
    setSelectedBlog,
    setShowBlogModal
  } = useBlogGenerator();

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
        onBulkDeleteBlogs={handleBulkDeleteBlogs}
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
              {/* Top inline status + progress */}
              {currentJob.status === 'in_progress' && (
                <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-6 py-3 flex flex-col gap-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-700 dark:text-gray-300 font-medium truncate">{currentJob.currentStep || 'Working...'}</span>
                    <span className="text-gray-500 dark:text-gray-400 tabular-nums">{Math.round(currentJob.progress)}%</span>
                  </div>
                  <ProgressBar value={currentJob.progress} />
                </div>
              )}

              <BlogGenerationView
                job={currentJob}
                isGenerating={isGenerating || currentJob.status === 'in_progress'}
                logs={currentJobId ? taskLogs[currentJobId] || [] : []}
              />

              {/* Unified action bar for all terminal / active states */}
              {(currentJob.status === 'completed' || currentJob.status === 'in_progress' || currentJob.status === 'failed') && (
                <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
                  <div className="max-w-4xl mx-auto flex flex-col sm:flex-row gap-3 sm:justify-between sm:items-center">
                    <div className="flex items-center gap-3">
                      <Button
                        variant="outline"
                        onClick={handleNewBlog}
                        disabled={isDeleting || currentJob.status === 'in_progress'}
                      >
                        New Blog
                      </Button>
                    </div>
                    {/* Delete/Cancel button removed per updated UX: deletion via blog cards only */}
                  </div>
                </div>
              )}

              {generationError && (
                <div className="px-6 py-4">
                  <ErrorBanner
                    message={generationError}
                    onClose={() => setGenerationError(null)}
                  />
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
                    Create engaging, well-researched blog posts with the power of AI. Our CrewAI-powered system researches, writes, and fact-checks your content automatically.
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
                  {generationError && (
                    <div className="mt-4">
                      <ErrorBanner
                        message={generationError}
                        onClose={() => setGenerationError(null)}
                      />
                    </div>
                  )}
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
