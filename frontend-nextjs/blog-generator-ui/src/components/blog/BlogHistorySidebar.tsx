import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ChevronLeft, ChevronRight, History, Plus, CheckSquare, Trash2, X } from 'lucide-react';
import { BlogData, JobState, SelectionState } from '@/types/blog';
import { ConfirmDeleteModal } from './ConfirmDeleteModal';
import { useState, useCallback } from 'react';

interface BlogHistorySidebarProps {
  blogs: BlogData[];
  jobs: JobState[];
  loading: boolean;
  collapsed: boolean;
  onToggleCollapse: () => void;
  onBlogClick: (blog: BlogData) => void;
  onJobClick: (jobId: string) => void;
  onDeleteBlog: (blogId: string) => void;
  onBulkDeleteBlogs: (blogIds: string[]) => void;
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
  onBulkDeleteBlogs,
  onNewBlog
}: BlogHistorySidebarProps) {

  // Selection state management
  const [selectionState, setSelectionState] = useState<SelectionState>({
    isSelectionMode: false,
    selectedBlogIds: new Set(),
    longPressTimer: null,
    targetBlogId: null,
    pulsingBlogId: null,
  });

  const [showDeleteModal, setShowDeleteModal] = useState(false);

  // Selection handlers
  const activateSelectionMode = useCallback((blogId: string) => {
    setSelectionState(prev => ({
      ...prev,
      isSelectionMode: true,
      selectedBlogIds: new Set([blogId]),
      longPressTimer: null,
      targetBlogId: null,
      pulsingBlogId: null,
    }));
  }, []);

  const exitSelectionMode = useCallback(() => {
    setSelectionState({
      isSelectionMode: false,
      selectedBlogIds: new Set(),
      longPressTimer: null,
      targetBlogId: null,
      pulsingBlogId: null,
    });
  }, []);

  const toggleBlogSelection = useCallback((blogId: string) => {
    setSelectionState(prev => {
      const newSelected = new Set(prev.selectedBlogIds);
      if (newSelected.has(blogId)) {
        newSelected.delete(blogId);
      } else {
        newSelected.add(blogId);
      }
      return { ...prev, selectedBlogIds: newSelected };
    });
  }, []);

  const selectAllBlogs = useCallback(() => {
    const allBlogIds = blogs.map(blog => blog.id);
    setSelectionState(prev => ({
      ...prev,
      selectedBlogIds: new Set(allBlogIds),
    }));
  }, [blogs]);

  const handleLongPress = useCallback((blogId: string) => {
    // Start pulsing animation immediately
    setSelectionState(prev => ({
      ...prev,
      pulsingBlogId: blogId,
      targetBlogId: blogId,
    }));

    // Set timer for 2 seconds to activate selection mode
    const timer = setTimeout(() => {
      activateSelectionMode(blogId);
    }, 2000);

    setSelectionState(prev => ({
      ...prev,
      longPressTimer: timer,
    }));
  }, [activateSelectionMode]);

  const handleMouseUp = useCallback(() => {
    if (selectionState.longPressTimer) {
      clearTimeout(selectionState.longPressTimer);
    }
    
    // Clear pulsing and target states
    setSelectionState(prev => ({
      ...prev,
      longPressTimer: null,
      targetBlogId: null,
      pulsingBlogId: null,
    }));
  }, [selectionState.longPressTimer]);

  const openDeleteConfirmation = useCallback(() => {
    setShowDeleteModal(true);
  }, []);

  const handleBulkDelete = useCallback(() => {
    const blogIdsToDelete = Array.from(selectionState.selectedBlogIds);
    onBulkDeleteBlogs(blogIdsToDelete);
    setShowDeleteModal(false);
    exitSelectionMode();
  }, [selectionState.selectedBlogIds, onBulkDeleteBlogs, exitSelectionMode]);

  const selectedBlogs = blogs.filter(blog => selectionState.selectedBlogIds.has(blog.id));

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

        {/* Selection Controls - only shown in selection mode */}
        {selectionState.isSelectionMode && (
          <div className="flex items-center justify-between px-3 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <span className="text-sm text-blue-700 dark:text-blue-300 font-medium">
              {selectionState.selectedBlogIds.size} selected
            </span>
            <div className="flex space-x-1">
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={selectAllBlogs}
                className="w-8 h-8 p-0 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                title="Select All"
              >
                <CheckSquare className="w-4 h-4" />
              </Button>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={openDeleteConfirmation}
                className="w-8 h-8 p-0 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                disabled={selectionState.selectedBlogIds.size === 0}
                title="Delete Selected"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={exitSelectionMode}
                className="w-8 h-8 p-0 text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
                title="Cancel"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
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
                      isSelectionMode={selectionState.isSelectionMode}
                      isSelected={selectionState.selectedBlogIds.has(blog.id)}
                      isPulsing={selectionState.pulsingBlogId === blog.id}
                      onSelectionToggle={toggleBlogSelection}
                      onLongPress={handleLongPress}
                      onMouseUp={handleMouseUp}
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

      {/* Confirmation Modal */}
      <ConfirmDeleteModal
        isOpen={showDeleteModal}
        selectedBlogs={selectedBlogs}
        onConfirm={handleBulkDelete}
        onCancel={() => setShowDeleteModal(false)}
      />
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
  onDelete,
  isSelectionMode = false,
  isSelected = false,
  isPulsing = false,
  onSelectionToggle,
  onLongPress,
  onMouseUp
}: {
  blog: BlogData;
  onClick: () => void;
  onDelete: () => void;
  isSelectionMode?: boolean;
  isSelected?: boolean;
  isPulsing?: boolean;
  onSelectionToggle?: (blogId: string) => void;
  onLongPress?: (blogId: string) => void;
  onMouseUp?: () => void;
}) {
  
  const handleMouseDown = () => {
    if (!isSelectionMode && onLongPress) {
      onLongPress(blog.id);
    }
  };

  const handleMouseUp = () => {
    if (onMouseUp) {
      onMouseUp();
    }
  };

  const handleClick = () => {
    if (isSelectionMode && onSelectionToggle) {
      onSelectionToggle(blog.id);
    } else {
      onClick();
    }
  };

  return (
    <Card 
      className={`p-3 cursor-pointer transition-all duration-200 group relative
        ${isSelectionMode ? 'border-dashed border-2 border-blue-300 dark:border-blue-600' : 'border border-gray-200 dark:border-gray-600'} 
        ${isSelected ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 border-solid' : ''}
        ${!isSelectionMode ? 'hover:bg-gray-50 dark:hover:bg-gray-700' : 'hover:bg-blue-50 dark:hover:bg-blue-900/10'}
        ${isPulsing ? 'long-press-pulse' : ''}
        bg-white dark:bg-gray-800`}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onClick={handleClick}
    >
      {/* Selection checkbox - positioned absolutely in top-left */}
      {isSelectionMode && (
        <div className="absolute top-2 left-2 z-10">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onSelectionToggle && onSelectionToggle(blog.id)}
            onClick={(e) => e.stopPropagation()}
            className="w-4 h-4 text-blue-600 bg-white border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
          />
        </div>
      )}

      <div className={`space-y-2 ${isSelectionMode ? 'ml-6' : ''}`}>
        <div className="flex items-start justify-between">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-2">
            {blog.topic}
          </h4>
          {/* Only show delete button in normal mode */}
          {!isSelectionMode && (
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
          )}
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
