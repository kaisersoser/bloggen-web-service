import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { BlogCard } from '@/components/blog/BlogCard';
import { JobState, BlogData } from '@/types/blog';

interface JobsDashboardProps {
  jobs: JobState[];
  previousBlogs: BlogData[];
  blogsLoading: boolean;
  hasMore: boolean;
  scrollLoading: boolean;
  onJobClick: (jobId: string) => void;
  onBlogClick: (blog: BlogData) => void;
  onDeleteJob: (jobId: string) => void;
  onDeleteBlog: (blogId: string) => void;
}

export function JobsDashboard({
  jobs,
  previousBlogs,
  blogsLoading,
  hasMore,
  scrollLoading,
  onJobClick,
  onBlogClick,
  onDeleteJob,
  onDeleteBlog
}: JobsDashboardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Blog Generation Jobs & History</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Active Jobs Section */}
        {jobs.length > 0 && (
          <div className="mb-8">
            <h3 className="text-lg font-semibold mb-4 text-gray-800">Active Jobs</h3>
            <div className="space-y-4">
              {jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  onJobClick={onJobClick}
                  onDeleteJob={onDeleteJob}
                />
              ))}
            </div>
          </div>
        )}

        {/* Previous Blogs Section */}
        <div>
          <h3 className="text-lg font-semibold mb-4 text-gray-800">Previous Blogs</h3>
          {blogsLoading ? (
            <div className="flex justify-center items-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : previousBlogs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No previous blogs yet. Create your first blog!
            </div>
          ) : (
            <div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {previousBlogs.map((blog) => (
                  <BlogCard
                    key={blog.id}
                    blog={blog}
                    onClick={onBlogClick}
                    onDelete={onDeleteBlog}
                  />
                ))}
              </div>
              
              {/* Infinite scroll sentinel */}
              {hasMore && (
                <div id="blog-scroll-sentinel" className="flex justify-center items-center py-8">
                  {scrollLoading ? (
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                  ) : (
                    <div className="text-sm text-gray-500">Scroll to load more blogs...</div>
                  )}
                </div>
              )}
              
              {!hasMore && previousBlogs.length > 6 && (
                <div className="text-center py-4">
                  <p className="text-sm text-gray-500">You&apos;ve reached the end of your blogs</p>
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// Job Card Component
function JobCard({
  job,
  onJobClick,
  onDeleteJob
}: {
  job: JobState;
  onJobClick: (jobId: string) => void;
  onDeleteJob: (jobId: string) => void;
}) {
  return (
    <div
      className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer"
      onClick={() => onJobClick(job.id)}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <h3 className="font-semibold text-lg">{job.topic}</h3>
          <p className="text-sm text-gray-600 mt-1">{job.currentStep}</p>
          <div className="flex items-center space-x-4 mt-2">
            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
              job.status === 'completed' ? 'bg-green-100 text-green-800' :
              job.status === 'failed' ? 'bg-red-100 text-red-800' :
              job.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {job.status.replace('_', ' ')}
            </span>
            <span className="text-xs text-gray-500">
              {new Date(job.createdAt).toLocaleString()}
            </span>
          </div>
          {job.status === 'in_progress' && (
            <div className="mt-2">
              <Progress value={job.progress} className="w-full" />
            </div>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              onJobClick(job.id);
            }}
          >
            View Details
          </Button>
          {job.status === 'completed' || job.status === 'failed' ? (
            <Button
              variant="destructive"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                onDeleteJob(job.id);
              }}
            >
              Delete
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
