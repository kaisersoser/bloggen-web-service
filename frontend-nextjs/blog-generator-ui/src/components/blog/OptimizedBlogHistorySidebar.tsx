// QUICK FIX 1: Optimize BlogHistorySidebar loading
// src/components/blog/BlogHistorySidebar.tsx (Enhancement)

import React, { useMemo } from 'react';

export function BlogHistorySidebar({ blogs, jobs, loading, ...props }: BlogHistorySidebarProps) {
  // Memoize sorted and filtered blogs to prevent re-computation
  const sortedBlogs = useMemo(() => {
    return blogs
      .slice() // Shallow copy to avoid mutating original
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  }, [blogs]);

  // Memoize active jobs to prevent unnecessary re-renders
  const activeJobs = useMemo(() => {
    return jobs.filter(job => job.status === 'in_progress');
  }, [jobs]);

  // Show skeleton with exact count instead of generic loading
  if (loading) {
    return (
      <div className="w-80 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex flex-col h-full">
        <div className="p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded mb-4"></div>
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {/* Show 5 skeleton cards instead of infinite loop */}
          {Array.from({ length: 5 }, (_, i) => (
            <BlogCardSkeleton key={`skeleton-${i}`} />
          ))}
        </div>
      </div>
    );
  }

  return (
    // ... rest of component with memoized data
  );
}

// Quick skeleton component
const BlogCardSkeleton = React.memo(() => (
  <div className="animate-pulse p-3 border border-gray-200 dark:border-gray-600 rounded-lg">
    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
    <div className="flex justify-between items-center">
      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-16"></div>
      <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
    </div>
  </div>
));
