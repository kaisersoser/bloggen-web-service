// src/hooks/useOptimizedBlogs.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { blogService } from '@/lib/services/blog';
import { BlogData } from '@/types/blog';

export function useOptimizedBlogs() {
  const queryClient = useQueryClient();
  
  // Cache blog list with 5-minute stale time
  const { data: blogs = [], isLoading, error } = useQuery({
    queryKey: ['blogs'],
    queryFn: blogService.getUserBlogs,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    refetchOnWindowFocus: false,
  });

  // Optimistic updates for blog deletion
  const deleteMutation = useMutation({
    mutationFn: blogService.deleteBlog,
    onMutate: async (blogId: string) => {
      await queryClient.cancelQueries({ queryKey: ['blogs'] });
      const previousBlogs = queryClient.getQueryData<BlogData[]>(['blogs']);
      queryClient.setQueryData<BlogData[]>(['blogs'], (old = []) => 
        old.filter(blog => blog.id !== blogId)
      );
      return { previousBlogs };
    },
    onError: (err, blogId, context) => {
      if (context?.previousBlogs) {
        queryClient.setQueryData(['blogs'], context.previousBlogs);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['blogs'] });
    },
  });

  // Bulk delete mutation
  const bulkDeleteMutation = useMutation({
    mutationFn: async (blogIds: string[]) => {
      await Promise.all(blogIds.map(id => blogService.deleteBlog(id)));
    },
    onMutate: async (blogIds: string[]) => {
      await queryClient.cancelQueries({ queryKey: ['blogs'] });
      const previousBlogs = queryClient.getQueryData<BlogData[]>(['blogs']);
      queryClient.setQueryData<BlogData[]>(['blogs'], (old = []) => 
        old.filter(blog => !blogIds.includes(blog.id))
      );
      return { previousBlogs };
    },
    onError: (err, blogIds, context) => {
      if (context?.previousBlogs) {
        queryClient.setQueryData(['blogs'], context.previousBlogs);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['blogs'] });
    },
  });

  // Blog generation mutation
  const generateMutation = useMutation({
    mutationFn: ({ topic, instructions }: { topic: string; instructions?: string }) =>
      blogService.generateBlog(topic, instructions),
    onSuccess: () => {
      // Invalidate blogs query to refetch updated list
      queryClient.invalidateQueries({ queryKey: ['blogs'] });
    },
  });

  return {
    blogs,
    isLoading,
    error,
    deleteBlog: deleteMutation.mutate,
    bulkDeleteBlogs: bulkDeleteMutation.mutate,
    generateBlog: generateMutation.mutate,
    isDeleting: deleteMutation.isPending || bulkDeleteMutation.isPending,
    isGenerating: generateMutation.isPending,
  };
}
