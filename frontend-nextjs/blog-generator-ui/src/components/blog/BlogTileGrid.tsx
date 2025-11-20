"use client"
import React, { useState, useMemo, useCallback, useRef, useEffect } from 'react';
import { BlogTile } from './BlogTile';
import { ConfirmDeleteModal } from './ConfirmDeleteModal';
import { Button } from "@/components/ui/button";
import { Search, Grid, List, SortAsc, SortDesc, CheckSquare, Trash2, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { SelectionState } from "@/types/blog";
import { FixedSizeGrid as VirtualGrid, FixedSizeList as VirtualList, type GridChildComponentProps, type ListChildComponentProps } from 'react-window';

interface BlogTileGridProps {
  blogs: any[];
  onBlogView: (blog: any) => void;
  onBlogDelete: (blog: any) => void;
  onBulkDeleteBlogs?: (blogIds: string[]) => void;
  isLoading?: boolean;
  className?: string;
  // Queue-related optional handlers
  onViewLogs?: (taskId: string) => void;
  onViewDraft?: (taskId: string) => void;
  onRetry?: (blogId: string) => void;
}

type SortOption = 'newest' | 'oldest' | 'title-asc' | 'title-desc';
type ViewMode = 'grid' | 'list';

export function BlogTileGrid({ 
  blogs, 
  onBlogView, 
  onBlogDelete,
  onBulkDeleteBlogs, 
  isLoading = false, 
  className = "",
  onViewLogs,
  onViewDraft,
  onRetry
}: BlogTileGridProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<SortOption>('newest');
  const [viewMode, setViewMode] = useState<ViewMode>('grid');

  // Selection state management
  const [selectionState, setSelectionState] = useState<SelectionState>({
    isSelectionMode: false,
    selectedBlogIds: new Set(),
    longPressTimer: null,
    targetBlogId: null,
    pulsingBlogId: null,
  });

  // Delete confirmation modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.offsetWidth);
      }
    };

    updateDimensions();

    if (typeof ResizeObserver !== 'undefined') {
      const observer = new ResizeObserver(() => updateDimensions());
      if (containerRef.current) {
        observer.observe(containerRef.current);
      }
      return () => observer.disconnect();
    }

    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // Filter and sort blogs
  const processedBlogs = useMemo(() => {
    const filtered = blogs.filter(blog => {
      const query = searchQuery.toLowerCase();
      const sortLabel = (blog.title || blog.topic || '').toLowerCase();
      const topic = blog.topic?.toLowerCase() || '';

      return sortLabel.includes(query) || topic.includes(query);
    });

    // Sort blogs
    switch (sortBy) {
      case 'newest':
        filtered.sort((a, b) => new Date(b.createdAt || 0).getTime() - new Date(a.createdAt || 0).getTime());
        break;
      case 'oldest':
        filtered.sort((a, b) => new Date(a.createdAt || 0).getTime() - new Date(b.createdAt || 0).getTime());
        break;
      case 'title-asc':
        filtered.sort((a, b) => (a.title || a.topic || '').localeCompare(b.title || b.topic || '', undefined, { sensitivity: 'base' }));
        break;
      case 'title-desc':
        filtered.sort((a, b) => (b.title || b.topic || '').localeCompare(a.title || a.topic || '', undefined, { sensitivity: 'base' }));
        break;
    }

    return filtered;
  }, [blogs, searchQuery, sortBy]);

  const columnCount = useMemo(() => {
    if (viewMode === 'list') {
      return 1;
    }
    if (containerWidth >= 1280) return 4;
    if (containerWidth >= 1024) return 3;
    if (containerWidth >= 768) return 2;
    return 1;
  }, [containerWidth, viewMode]);

  const rowHeight = viewMode === 'grid' ? 420 : 200;
  const columnWidth = useMemo(() => {
    if (containerWidth === 0) {
      return 0;
    }
    return containerWidth / Math.max(columnCount, 1);
  }, [columnCount, containerWidth]);

  const gridRowCount = useMemo(() => Math.ceil(processedBlogs.length / Math.max(columnCount, 1)), [columnCount, processedBlogs.length]);

  const virtualHeight = useMemo(() => {
    const totalRows = viewMode === 'grid'
      ? gridRowCount
      : processedBlogs.length;
    const calculatedHeight = totalRows * rowHeight;
    return Math.max(rowHeight, Math.min(calculatedHeight, 900));
  }, [gridRowCount, processedBlogs.length, rowHeight, viewMode]);

  const shouldVirtualizeGrid = viewMode === 'grid' && processedBlogs.length > columnCount * 2 && containerWidth > 0;
  const shouldVirtualizeList = viewMode === 'list' && processedBlogs.length > 20 && containerWidth > 0;

  // Selection handlers
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
    const allBlogIds = processedBlogs.map(blog => blog.id);
    setSelectionState(prev => ({
      ...prev,
      selectedBlogIds: new Set(allBlogIds),
    }));
  }, [processedBlogs]);

  const handleLongPress = useCallback((blogId: string) => {
    if (!selectionState.isSelectionMode) {
      // Start long press timer to enable selection mode
      const timer = setTimeout(() => {
        setSelectionState({
          isSelectionMode: true,
          selectedBlogIds: new Set([blogId]),
          longPressTimer: null,
          targetBlogId: null,
          pulsingBlogId: null,
        });
      }, 1000); // 1 second long press
      
      setSelectionState(prev => ({
        ...prev,
        longPressTimer: timer,
        targetBlogId: blogId,
        pulsingBlogId: blogId,
      }));
    }
  }, [selectionState.isSelectionMode]);

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

  const handleBulkDelete = useCallback(() => {
    if (selectionState.selectedBlogIds.size > 0) {
      setShowDeleteModal(true);
    }
  }, [selectionState.selectedBlogIds]);

  const confirmBulkDelete = useCallback(() => {
    if (onBulkDeleteBlogs && selectionState.selectedBlogIds.size > 0) {
      const blogIdsToDelete = Array.from(selectionState.selectedBlogIds);
      onBulkDeleteBlogs(blogIdsToDelete);
      setShowDeleteModal(false);
      exitSelectionMode();
    }
  }, [onBulkDeleteBlogs, selectionState.selectedBlogIds, exitSelectionMode]);

  const cancelBulkDelete = useCallback(() => {
    setShowDeleteModal(false);
  }, []);

  // Get selected blogs for the modal
  const selectedBlogs = processedBlogs.filter(blog => selectionState.selectedBlogIds.has(blog.id));

  const getSortIcon = () => {
    switch (sortBy) {
      case 'newest':
      case 'title-desc':
        return <SortDesc className="w-4 h-4" />;
      case 'oldest':
      case 'title-asc':
        return <SortAsc className="w-4 h-4" />;
      default:
        return <SortDesc className="w-4 h-4" />;
    }
  };

  const renderGridItem = useCallback(({ columnIndex, rowIndex, style }: GridChildComponentProps) => {
    const index = rowIndex * columnCount + columnIndex;
    if (index >= processedBlogs.length) {
      return null;
    }

    const blog = processedBlogs[index];

    return (
      <div style={{ ...style, padding: 12, boxSizing: 'border-box' }}>
        <BlogTile
          blog={blog}
          onView={onBlogView}
          onDelete={onBlogDelete}
          isSelectionMode={selectionState.isSelectionMode}
          isSelected={selectionState.selectedBlogIds.has(blog.id)}
          isPulsing={selectionState.pulsingBlogId === blog.id}
          onSelectionToggle={toggleBlogSelection}
          onLongPress={handleLongPress}
          onMouseUp={handleMouseUp}
          onViewLogs={onViewLogs}
          onViewDraft={onViewDraft}
          onRetry={onRetry}
          className="h-full"
        />
      </div>
    );
  }, [columnCount, handleLongPress, handleMouseUp, onBlogDelete, onBlogView, onViewLogs, onViewDraft, onRetry, processedBlogs, selectionState.isSelectionMode, selectionState.pulsingBlogId, selectionState.selectedBlogIds, toggleBlogSelection]);

  const renderListItem = useCallback(({ index, style }: ListChildComponentProps) => {
    const blog = processedBlogs[index];

    return (
      <div style={{ ...style, padding: 12, boxSizing: 'border-box' }}>
        <BlogTile
          blog={blog}
          onView={onBlogView}
          onDelete={onBlogDelete}
          isSelectionMode={selectionState.isSelectionMode}
          isSelected={selectionState.selectedBlogIds.has(blog.id)}
          isPulsing={selectionState.pulsingBlogId === blog.id}
          onSelectionToggle={toggleBlogSelection}
          onLongPress={handleLongPress}
          onMouseUp={handleMouseUp}
          onViewLogs={onViewLogs}
          onViewDraft={onViewDraft}
          onRetry={onRetry}
          className="w-full"
        />
      </div>
    );
  }, [handleLongPress, handleMouseUp, onBlogDelete, onBlogView, onViewLogs, onViewDraft, onRetry, processedBlogs, selectionState.isSelectionMode, selectionState.pulsingBlogId, selectionState.selectedBlogIds, toggleBlogSelection]);

  const gridItemKey = useCallback(({ columnIndex, rowIndex }: { columnIndex: number; rowIndex: number }) => {
    const index = rowIndex * columnCount + columnIndex;
    return processedBlogs[index]?.id ?? `${rowIndex}-${columnIndex}`;
  }, [columnCount, processedBlogs]);

  const listItemKey = useCallback((index: number) => processedBlogs[index]?.id ?? index, [processedBlogs]);

  if (isLoading) {
    return (
      <div className={`${className}`}>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, index) => (
            <div key={index} className="animate-pulse">
              <div className="bg-gray-200 dark:bg-gray-700 rounded-lg aspect-[16/10] mb-4"></div>
              <div className="space-y-2">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Search and Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              type="text"
              placeholder="Search blogs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Sort Dropdown */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="title-asc">Title A-Z</option>
            <option value="title-desc">Title Z-A</option>
          </select>

          {/* View Mode Toggle */}
          <div className="flex border border-gray-300 dark:border-gray-600 rounded-md overflow-hidden">
            <Button
              size="sm"
              variant={viewMode === 'grid' ? 'default' : 'ghost'}
              onClick={() => setViewMode('grid')}
              className="rounded-none border-none"
            >
              <Grid className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant={viewMode === 'list' ? 'default' : 'ghost'}
              onClick={() => setViewMode('list')}
              className="rounded-none border-none"
            >
              <List className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Results Count */}
      <div className="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
        <span>
          {processedBlogs.length} {processedBlogs.length === 1 ? 'blog' : 'blogs'}
          {searchQuery && ` matching "${searchQuery}"`}
        </span>
        <div className="flex items-center gap-1">
          {getSortIcon()}
          <span className="text-xs">
            {sortBy === 'newest' ? 'Newest first' : 
             sortBy === 'oldest' ? 'Oldest first' :
             sortBy === 'title-asc' ? 'A-Z' : 'Z-A'}
          </span>
        </div>
      </div>

      {/* Selection Controls - only shown in selection mode */}
      {selectionState.isSelectionMode && (
        <div className="flex items-center justify-between px-4 py-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-4">
            <span className="text-sm text-blue-700 dark:text-blue-300 font-medium">
              {selectionState.selectedBlogIds.size} blog{selectionState.selectedBlogIds.size !== 1 ? 's' : ''} selected
            </span>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={selectAllBlogs}
              className="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
              title="Select All"
            >
              <CheckSquare className="w-4 h-4 mr-1" />
              Select All
            </Button>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={handleBulkDelete}
              className="text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
              disabled={selectionState.selectedBlogIds.size === 0}
              title="Delete Selected"
            >
              <Trash2 className="w-4 h-4 mr-1" />
              Delete Selected
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={exitSelectionMode}
              className="text-gray-600 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
              title="Cancel Selection"
            >
              <X className="w-4 h-4 mr-1" />
              Cancel
            </Button>
          </div>
        </div>
      )}

      {/* Blog Grid/List */}
      {processedBlogs.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 dark:text-gray-500 mb-4">
            <Grid className="w-16 h-16 mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-medium mb-2">No blogs found</h3>
            <p className="text-sm">
              {searchQuery ? `No blogs match "${searchQuery}"` : 'Start by generating your first blog!'}
            </p>
          </div>
        </div>
      ) : (
        <div ref={containerRef} className="relative w-full">
          {shouldVirtualizeGrid ? (
            <VirtualGrid
              height={virtualHeight}
              width={containerWidth || Math.max(columnCount * 320, 320)}
              columnCount={columnCount}
              columnWidth={columnWidth || 320}
              rowCount={gridRowCount}
              rowHeight={rowHeight}
              itemKey={gridItemKey}
              overscanRowCount={2}
              overscanColumnCount={1}
            >
              {renderGridItem}
            </VirtualGrid>
          ) : shouldVirtualizeList ? (
            <VirtualList
              height={virtualHeight}
              width={containerWidth || '100%'}
              itemCount={processedBlogs.length}
              itemSize={rowHeight}
              itemKey={listItemKey}
              overscanCount={3}
            >
              {renderListItem}
            </VirtualList>
          ) : (
            <div className={
              viewMode === 'grid'
                ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
                : "flex flex-col gap-4"
            }>
              {processedBlogs.map((blog) => (
                <BlogTile
                  key={blog.id}
                  blog={blog}
                  onView={onBlogView}
                  onDelete={onBlogDelete}
                  isSelectionMode={selectionState.isSelectionMode}
                  isSelected={selectionState.selectedBlogIds.has(blog.id)}
                  isPulsing={selectionState.pulsingBlogId === blog.id}
                  onSelectionToggle={toggleBlogSelection}
                  onLongPress={handleLongPress}
                  onMouseUp={handleMouseUp}
                  onViewLogs={onViewLogs}
                  onViewDraft={onViewDraft}
                  onRetry={onRetry}
                  className={viewMode === 'list' ? 'max-w-none' : ''}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Confirm Delete Modal */}
      <ConfirmDeleteModal
        isOpen={showDeleteModal}
        selectedBlogs={selectedBlogs}
        onConfirm={confirmBulkDelete}
        onCancel={cancelBulkDelete}
      />
    </div>
  );
}
