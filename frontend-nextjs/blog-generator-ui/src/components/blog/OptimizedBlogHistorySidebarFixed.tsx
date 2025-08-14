// src/components/blog/OptimizedBlogHistorySidebarFixed.tsx
import React from 'react';
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
  onBulkDeleteBlogs: (blogIds: string[]) => void;
  onNewBlog: () => void;
}

interface JobCardProps {
  job: JobState;
  onClick: () => void;
}

interface BlogCardProps {
  blog: BlogData;
  onClick: () => void;
}

// Skeleton components for loading states
const BlogCardSkeleton: React.FC = () => (
  <div className="animate-pulse p-4 border rounded-lg">
    <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
    <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
    <div className="h-3 bg-gray-200 rounded w-1/4"></div>
  </div>
);

const BlogHistorySkeleton: React.FC = () => (
  <div className="space-y-3 p-4">
    {Array.from({ length: 5 }).map((_, i) => (
      <BlogCardSkeleton key={i} />
    ))}
  </div>
);

const JobCard: React.FC<JobCardProps> = React.memo(({ job, onClick }) => (
  <div onClick={onClick} className="p-2 border rounded cursor-pointer hover:bg-gray-50">
    <div className="text-sm font-medium">{job.topic}</div>
    <div className="text-xs text-muted-foreground">{job.status}</div>
  </div>
));
JobCard.displayName = 'JobCard';

const BlogCard: React.FC<BlogCardProps> = React.memo(({ blog, onClick }) => (
  <div onClick={onClick} className="p-2 border rounded cursor-pointer hover:bg-gray-50">
    <div className="text-sm font-medium line-clamp-2">{blog.topic}</div>
    <div className="text-xs text-muted-foreground">
      {new Date(blog.createdAt).toLocaleDateString()}
    </div>
  </div>
));
BlogCard.displayName = 'BlogCard';

export const OptimizedBlogHistorySidebar: React.FC<BlogHistorySidebarProps> = React.memo(function OptimizedBlogHistorySidebar({ 
  blogs, 
  jobs, 
  loading, 
  ...props 
}) {
  // Memoize sorted blogs to prevent re-computation
  const sortedBlogs = React.useMemo(() => {
    return blogs
      .sort((a: BlogData, b: BlogData) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
  }, [blogs]);

  // Memoize active jobs
  const activeJobs = React.useMemo(() => {
    return jobs.filter((job: JobState) => job.status === 'in_progress');
  }, [jobs]);

  if (loading) {
    return <BlogHistorySkeleton />;
  }

  return (
    <div className="space-y-3">
      {/* Active jobs section */}
      {activeJobs.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-muted-foreground">Active Jobs</h3>
          {activeJobs.map(job => (
            <JobCard key={job.id} job={job} onClick={() => props.onJobClick?.(job.id)} />
          ))}
        </div>
      )}
      
      {/* Blogs section */}
      <div className="space-y-2">
        <h3 className="text-sm font-medium text-muted-foreground">Recent Blogs</h3>
        {sortedBlogs.map(blog => (
          <BlogCard 
            key={blog.id} 
            blog={blog} 
            onClick={() => props.onBlogClick?.(blog)}
          />
        ))}
      </div>
    </div>
  );
});
