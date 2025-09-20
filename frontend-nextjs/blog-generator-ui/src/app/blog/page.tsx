"use client"
import { Button } from "@/components/ui/button";
import { UserProfileDropdown } from "@/components/auth/UserProfileDropdown";
import { CenterChatInterface } from "@/components/blog/CenterChatInterface";
import { BlogTileGrid } from "@/components/blog/BlogTileGrid";
import { BlogViewModal } from "@/components/blog/BlogViewModal";
import { DeleteConfirmationDialog } from "@/components/blog/DeleteConfirmationDialog";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { AdminDiagnosticMonitor } from "@/components/diagnostics/AdminDiagnosticMonitor";
import { useTheme } from "@/components/theme/ThemeProvider";
import { useBlogGenerator } from "@/hooks/useBlogGenerator";
import { signIn } from "next-auth/react";

export default function BlogGenerator() {
  const { theme, setTheme } = useTheme();

  const {
    isAuthenticated,
    isLoading,
    stats,
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
    handleBlogClick,
    handleBulkDeleteBlogs,
    confirmDeleteBlog,
    setBlogToDelete,
    setIsDeleting,
    setSelectedBlog,
    setShowBlogModal,
    setShowDeleteDialog,
    setGenerationError
  } = useBlogGenerator();

  // Phase 4 Progressive Content Streaming - Future enhancement placeholder
  // SSE connection is handled by useBlogGenerator hook

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
        {/* Center Chat Interface */}
        <div className="flex justify-center">
          <CenterChatInterface
            onSubmit={(prompt) => handleGenerateBlog(prompt, '')}
            isGenerating={isGenerating}
            disabled={false}
            remainingGenerations={stats?.remainingGenerations}
            userRole={stats?.role as 'FREE' | 'PREMIUM' | 'ADMIN'}
          />
        </div>

        {/* Generation Progress (when active) */}
        {currentJobId && currentJob && currentJob.status === 'in_progress' && (
          <div className="max-w-4xl mx-auto">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 shadow-sm">
              <div className="flex items-center justify-between text-sm mb-3">
                <span className="text-gray-700 dark:text-gray-300 font-medium">
                  {currentJob.currentStep || 'Processing your request...'}
                </span>
                <span className="text-gray-500 dark:text-gray-400 tabular-nums">
                  {Math.round(currentJob.progress)}%
                </span>
              </div>
              <ProgressBar value={currentJob.progress} showLabel={false} />
              {/* Debug info */}
              <div className="text-xs text-gray-400 mt-1">
                Debug: progress={currentJob.progress}, rounded={Math.round(currentJob.progress)}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                AI agents are collaborating to create your blog. This may take a few minutes.
              </p>
            </div>
          </div>
        )}

        {/* Admin Diagnostic Monitor */}
        <div className="max-w-4xl mx-auto">
          <AdminDiagnosticMonitor 
            currentJobId={currentJobId}
            isGenerating={isGenerating}
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

        {/* Blog Tile Grid */}
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
    </div>
  );
}
