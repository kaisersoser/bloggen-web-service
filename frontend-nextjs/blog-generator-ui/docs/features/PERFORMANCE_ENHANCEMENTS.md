# Frontend Performance Enhancement Plan

## 🎯 Priority 1: Critical Performance Fixes

### 1.1 Data Fetching & Caching Layer
**Current Issue**: Every blog load triggers fresh API calls
**Solution**: Implement React Query/TanStack Query

```tsx
// New: src/hooks/useOptimizedBlogs.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { blogService } from '@/lib/services/blog';

export function useOptimizedBlogs() {
  const queryClient = useQueryClient();
  
  // Cache blog list with 5-minute stale time
  const { data: blogs, isLoading } = useQuery({
    queryKey: ['blogs'],
    queryFn: blogService.getUserBlogs,
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  });

  // Optimistic updates for blog deletion
  const deleteMutation = useMutation({
    mutationFn: blogService.deleteBlog,
    onMutate: async (blogId) => {
      await queryClient.cancelQueries(['blogs']);
      const previousBlogs = queryClient.getQueryData(['blogs']);
      queryClient.setQueryData(['blogs'], (old: any[]) => 
        old?.filter(blog => blog.id !== blogId) || []
      );
      return { previousBlogs };
    },
    onError: (err, blogId, context) => {
      queryClient.setQueryData(['blogs'], context?.previousBlogs);
    },
  });

  return { blogs, isLoading, deleteBlog: deleteMutation.mutate };
}
```

### 1.2 Virtual Scrolling for Blog List
**Current Issue**: All blogs rendered simultaneously
**Solution**: React-Window for virtualized lists

```tsx
// New: src/components/blog/VirtualizedBlogList.tsx
import { FixedSizeList as List } from 'react-window';
import { BlogHistoryCard } from './BlogHistoryCard';

interface VirtualizedBlogListProps {
  blogs: BlogData[];
  height: number;
  onBlogClick: (blog: BlogData) => void;
}

const ITEM_HEIGHT = 80;

export function VirtualizedBlogList({ blogs, height, onBlogClick }: VirtualizedBlogListProps) {
  const renderBlogItem = ({ index, style }: { index: number; style: React.CSSProperties }) => (
    <div style={style}>
      <BlogHistoryCard
        blog={blogs[index]}
        onClick={() => onBlogClick(blogs[index])}
      />
    </div>
  );

  return (
    <List
      height={height}
      itemCount={blogs.length}
      itemSize={ITEM_HEIGHT}
      overscanCount={5} // Render 5 extra items for smooth scrolling
    >
      {renderBlogItem}
    </List>
  );
}
```

### 1.3 Memoization & Performance Optimization
**Current Issue**: Excessive re-renders on state changes
**Solution**: React.memo and useMemo optimizations

```tsx
// Enhanced: src/components/blog/BlogHistoryCard.tsx
import React from 'react';

export const BlogHistoryCard = React.memo(({ 
  blog, 
  onClick, 
  onDelete,
  isSelectionMode = false 
}: BlogHistoryCardProps) => {
  // Component implementation with memo optimization
}, (prevProps, nextProps) => {
  // Custom comparison for optimal re-rendering
  return (
    prevProps.blog.id === nextProps.blog.id &&
    prevProps.isSelectionMode === nextProps.isSelectionMode &&
    prevProps.blog.status === nextProps.blog.status
  );
});
```

## 🎯 Priority 2: Advanced Performance Optimizations

### 2.1 Code Splitting & Lazy Loading
**Solution**: Dynamic imports for route-based splitting

```tsx
// Enhanced: src/app/layout.tsx
import dynamic from 'next/dynamic';

// Lazy load heavy components
const BlogGenerator = dynamic(() => import('./blog/page'), {
  loading: () => <BlogGeneratorSkeleton />
});

const UserDashboard = dynamic(() => import('./dashboard/page'), {
  loading: () => <DashboardSkeleton />
});
```

### 2.2 SSE Connection Optimization
**Current Issue**: SSE connection causes UI blocking
**Solution**: Web Workers for background processing

```tsx
// New: src/workers/sseWorker.ts
self.onmessage = function(e) {
  const { type, taskId, token } = e.data;
  
  if (type === 'CONNECT_SSE') {
    const eventSource = new EventSource(`/api/stream/${taskId}?token=${token}`);
    
    eventSource.onmessage = (event) => {
      self.postMessage({
        type: 'SSE_MESSAGE',
        data: JSON.parse(event.data)
      });
    };
    
    eventSource.onerror = () => {
      self.postMessage({ type: 'SSE_ERROR' });
    };
  }
};
```

### 2.3 State Management Optimization
**Solution**: Zustand for lighter state management

```tsx
// New: src/store/blogStore.ts
import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

interface BlogStore {
  blogs: BlogData[];
  jobs: JobState[];
  currentJobId: string | null;
  isGenerating: boolean;
  
  // Actions
  setBlogs: (blogs: BlogData[]) => void;
  addJob: (job: JobState) => void;
  updateJob: (jobId: string, updates: Partial<JobState>) => void;
}

export const useBlogStore = create<BlogStore>()(
  subscribeWithSelector((set, get) => ({
    blogs: [],
    jobs: [],
    currentJobId: null,
    isGenerating: false,
    
    setBlogs: (blogs) => set({ blogs }),
    addJob: (job) => set((state) => ({ 
      jobs: [...state.jobs, job] 
    })),
    updateJob: (jobId, updates) => set((state) => ({
      jobs: state.jobs.map(job => 
        job.id === jobId ? { ...job, ...updates } : job
      )
    }))
  }))
);
```

## 🎯 Priority 3: User Experience Enhancements

### 3.1 Skeleton Loading States
**Solution**: Comprehensive loading skeletons

```tsx
// New: src/components/ui/skeletons.tsx
export function BlogCardSkeleton() {
  return (
    <div className="animate-pulse p-4 border rounded-lg">
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
      <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
      <div className="h-3 bg-gray-200 rounded w-1/4"></div>
    </div>
  );
}

export function BlogHistorySkeleton() {
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <BlogCardSkeleton key={i} />
      ))}
    </div>
  );
}
```

### 3.2 Optimistic UI Updates
**Solution**: Immediate feedback for user actions

```tsx
// Enhanced: src/hooks/useOptimisticBlogActions.ts
export function useOptimisticBlogActions() {
  const [optimisticBlogs, setOptimisticBlogs] = useState<BlogData[]>([]);
  
  const deleteBlogs = async (blogIds: string[]) => {
    // Immediately remove from UI
    setOptimisticBlogs(prev => 
      prev.filter(blog => !blogIds.includes(blog.id))
    );
    
    try {
      await Promise.all(blogIds.map(id => blogService.deleteBlog(id)));
      // Success - optimistic update was correct
    } catch (error) {
      // Revert optimistic update
      fetchBlogs(); // Re-fetch to restore state
      throw error;
    }
  };
  
  return { optimisticBlogs, deleteBlogs };
}
```

### 3.3 Progressive Loading
**Solution**: Incremental content loading

```tsx
// New: src/components/blog/ProgressiveBlogLoader.tsx
export function ProgressiveBlogLoader() {
  const [loadedSections, setLoadedSections] = useState<Set<string>>(new Set());
  
  useEffect(() => {
    // Load sections progressively
    const timer1 = setTimeout(() => setLoadedSections(prev => new Set([...prev, 'header'])), 100);
    const timer2 = setTimeout(() => setLoadedSections(prev => new Set([...prev, 'sidebar'])), 300);
    const timer3 = setTimeout(() => setLoadedSections(prev => new Set([...prev, 'content'])), 500);
    
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
    };
  }, []);
  
  return (
    <div className="h-screen flex">
      {loadedSections.has('sidebar') && <BlogHistorySidebar />}
      {loadedSections.has('content') && <MainContent />}
    </div>
  );
}
```

## 🎯 Priority 4: Bundle Optimization

### 4.1 Next.js Bundle Analyzer
**Solution**: Analyze and optimize bundle size

```bash
# Install bundle analyzer
npm install --save-dev @next/bundle-analyzer

# Add to next.config.ts
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

module.exports = withBundleAnalyzer({
  // existing config
});
```

### 4.2 Tree Shaking Optimization
**Solution**: Selective imports and dynamic loading

```tsx
// Before: Import entire library
import * as LucideIcons from 'lucide-react';

// After: Import only needed icons
import { Terminal, Settings, Plus } from 'lucide-react';

// Dynamic loading for heavy components
const ReactMarkdown = dynamic(() => import('react-markdown'), {
  loading: () => <div>Loading content...</div>
});
```

## 🛠️ Implementation Priority

1. **Week 1**: React Query integration, basic memoization
2. **Week 2**: Virtual scrolling, skeleton loading states  
3. **Week 3**: Code splitting, Web Worker SSE
4. **Week 4**: Zustand migration, bundle optimization

## 📊 Expected Performance Gains

- **Initial Load Time**: 40-60% improvement
- **Blog List Rendering**: 70-80% improvement  
- **SSE Connection Responsiveness**: 50-70% improvement
- **Bundle Size**: 30-50% reduction
- **Memory Usage**: 20-40% reduction

## 🔧 Monitoring & Metrics

```tsx
// New: src/utils/performance.ts
export function measurePerformance(name: string, fn: () => void) {
  performance.mark(`${name}-start`);
  fn();
  performance.mark(`${name}-end`);
  performance.measure(name, `${name}-start`, `${name}-end`);
  
  const measure = performance.getEntriesByName(name)[0];
  console.log(`${name} took ${measure.duration.toFixed(2)}ms`);
}

export function trackBlogLoadTime() {
  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.name === 'blog-list-render') {
        console.log(`Blog list rendered in ${entry.duration}ms`);
      }
    }
  });
  observer.observe({ entryTypes: ['measure'] });
}
```
