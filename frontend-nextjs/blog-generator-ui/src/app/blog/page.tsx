"use client"
import dynamic from "next/dynamic";
import { Button } from "@/components/ui/button";
import { UserProfileDropdown } from "@/components/auth/UserProfileDropdown";
import { TabbedPromptInterface } from "@/components/blog/TabbedPromptInterface";
import { BlogTileGrid } from "@/components/blog/BlogTileGrid";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { useTheme } from "@/components/theme/ThemeProvider";
import { useBlogGenerator } from "@/hooks/useBlogGenerator";
import { signIn } from "next-auth/react";
import { logger } from "@/lib/logger";

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

  // Debug logging to track duplicate blog cards
  logger.debug('Blog page render debug', {
    jobsCount: jobs?.length || 0,
    previousBlogsCount: previousBlogs?.length || 0,
    jobsData: jobs?.map(j => ({ id: j.id, topic: j.topic, status: j.status })) || [],
    previousBlogsData: previousBlogs?.map(b => ({ id: b.id, topic: b.topic, status: b.status, hasContent: !!b.content, hasHeroImage: !!b.heroImageUrl })) || []
  });

  const activeConnectionStatus = currentJob?.connectionState ? {
    status: currentJob.connectionState,
    message: currentJob.connectionMessage,
    updatedAt: currentJob.connectionUpdatedAt,
  } : null;

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
