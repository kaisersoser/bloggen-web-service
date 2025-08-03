import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ChevronLeft, ChevronRight, History, Plus } from 'lucide-react';
import { BlogData, JobState } from '@/types/blog';

interface BlogHistorySidebarProps {
  blogs: BlogData[];
  jobs: JobState[];
  loading: boolean;
  collapsed: boolean;
  onToggleCollapse: () => void;
  onBlogClick: (blog: BlogData) => void;
  onJobClick: (jobId: string) => void;
  onDeleteBlog: (blogId: string) => void;
  onNewBlog: () => void;
}

export function BlogHistorySidebar({
  blogs,
  jobs,
  loading,
  collapsed,
  onToggleCollapse,
  onBlogClick,
  onJobClick,
  onDeleteBlog,
  onNewBlog
}: BlogHistorySidebarProps) {

  if (collapsed) {
    return (
      <div className="w-12 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex flex-col items-center py-4 space-y-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={onToggleCollapse}
          className="w-8 h-8 p-0"
        >
          <ChevronRight className="w-4 h-4" />
        </Button>
        
        <Button
          variant="ghost"
          size="sm"
          onClick={onNewBlog}
          className="w-8 h-8 p-0"
        >
          <Plus className="w-4 h-4" />
        </Button>
        
        <div className="flex-1 flex items-center">
          <History className="w-4 h-4 text-gray-400 dark:text-gray-500" />
        </div>
      </div>
    );
  }

  return (
    <div className="w-80 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Generated Blogs</h2>
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggleCollapse}
            className="w-8 h-8 p-0"
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
        </div>
        
        <Button
          onClick={onNewBlog}
          className="w-full"
          size="sm"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Blog
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-4 space-y-3">
          {loading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="animate-pulse">
                  <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded-lg"></div>
                </div>
              ))}
            </div>
          ) : (
            <>
              {/* Active Jobs */}
              {jobs.filter(job => job.status === 'in_progress').length > 0 && (
                <div className="mb-4">
                  <h3 className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
                    In Progress
                  </h3>
                  <div className="space-y-2">
                    {jobs.filter(job => job.status === 'in_progress').map((job) => (
                      <JobHistoryCard
                        key={`active-job-${job.id}`}
                        job={job}
                        onClick={() => onJobClick(job.id)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* All Blogs */}
              <div className="space-y-2">
                {blogs.length > 0 ? (
                  blogs.map((blog) => (
                    <BlogHistoryCard
                      key={`blog-${blog.id}`}
                      blog={blog}
                      onClick={() => onBlogClick(blog)}
                      onDelete={() => onDeleteBlog(blog.id)}
                    />
                  ))
                ) : (
                  <div className="text-center py-8">
                    <History className="w-8 h-8 text-gray-400 dark:text-gray-500 mx-auto mb-2" />
                    <p className="text-sm text-gray-500 dark:text-gray-400">No blogs created yet</p>
                    <Button
                      onClick={onNewBlog}
                      variant="outline"
                      size="sm"
                      className="mt-2"
                    >
                      Create your first blog
                    </Button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// Job History Card Component
function JobHistoryCard({
  job,
  onClick
}: {
  job: JobState;
  onClick: () => void;
}) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30';
      case 'failed':
        return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30';
      case 'in_progress':
        return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30';
      default:
        return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700';
    }
  };

  return (
    <Card 
      className="p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800"
      onClick={onClick}
    >
      <div className="space-y-2">
        <div className="flex items-start justify-between">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-2">
            {job.topic}
          </h4>
          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(job.status)}`}>
            {job.status === 'in_progress' ? 'Generating...' : job.status}
          </span>
        </div>
        
        {job.status === 'in_progress' && (
          <div className="space-y-1">
            <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-1">
              <div 
                className="bg-blue-600 dark:bg-blue-400 h-1 rounded-full transition-all duration-300"
                style={{ width: `${job.progress}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">{job.currentStep}</p>
          </div>
        )}
        
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {new Date(job.createdAt).toLocaleDateString()}
        </p>
      </div>
    </Card>
  );
}

// Blog History Card Component  
function BlogHistoryCard({
  blog,
  onClick,
  onDelete
}: {
  blog: BlogData;
  onClick: () => void;
  onDelete: () => void;
}) {
  return (
    <Card 
      className="p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors group border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800"
      onClick={onClick}
    >
      <div className="space-y-2">
        <div className="flex items-start justify-between">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-2">
            {blog.topic}
          </h4>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="opacity-0 group-hover:opacity-100 transition-opacity w-6 h-6 p-0 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400"
          >
            ×
          </Button>
        </div>
        
        <div className="flex items-center justify-between">
          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
            blog.status === 'completed' 
              ? 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30' 
              : 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700'
          }`}>
            {blog.status}
          </span>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {new Date(blog.createdAt).toLocaleDateString()}
          </p>
        </div>
      </div>
    </Card>
  );
}
