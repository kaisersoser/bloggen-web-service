import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BlogCard } from '@/components/blog/BlogCard';
import { BlogData } from '@/types/blog';

interface PreviousBlogsSectionProps {
  blogs: BlogData[];
  loading: boolean;
  hasMore: boolean;
  scrollLoading: boolean;
  onBlogClick: (blog: BlogData) => void;
  onDeleteBlog: (blogId: string) => void;
}

export function PreviousBlogsSection({
  blogs,
  loading,
  hasMore,
  scrollLoading,
  onBlogClick,
  onDeleteBlog
}: PreviousBlogsSectionProps) {
  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle>Previous Blogs</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex justify-center items-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : blogs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No previous blogs yet. Generate your first blog above!
          </div>
        ) : (
          <div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {blogs.map((blog) => (
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
            
            {!hasMore && blogs.length > 6 && (
              <div className="text-center py-4">
                <p className="text-sm text-gray-500">You&apos;ve reached the end of your blogs</p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
