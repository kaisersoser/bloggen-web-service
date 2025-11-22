import { BlogData, BlogGenerationResponse, ApiBlogDto, mapApiBlog, ErrorInfo } from '@/types/blog';
import { QueueStatus, GenerationLog, DraftContent } from '@/types/queue';
import { api } from '../api-client';
import { getBackendUrl } from '@/config/protocol';
import { logger } from '@/lib/logger';
import { VERBOSE_LOGGING_ENABLED } from '@/lib/logger/env';
import { authTokenManager, AuthTokenError } from '@/lib/authTokenManager';

class BlogService {
  async generateTaskId(): Promise<string> {
    const response = await api.blogs.generateTaskId();
    
    if (!response.success) {
      const errorData = response.data as { message?: string; error?: string };
      throw new Error(errorData?.message || errorData?.error || "Failed to generate task ID");
    }
    
    return (response.data as { task_id: string }).task_id;
  }

  async generateBlog(topic: string, instructions?: string, taskId?: string): Promise<BlogGenerationResponse> {
    const response = await api.blogs.generate(topic, instructions, taskId);
    
    if (!response.success) {
      const errorData = response.data as { message?: string; error?: string };
      throw new Error(errorData?.message || errorData?.error || "Failed to start blog generation");
    }
    
    return response.data as BlogGenerationResponse;
  }

  async getUserBlogs(): Promise<BlogData[]> {
    const response = await api.blogs.list();
    if (!response.success) {
      throw new Error('Failed to fetch blogs');
    }
    const raw: ApiBlogDto[] = (response.data as any)?.blogs || [];
    return raw.map(mapApiBlog);
  }

  async deleteBlog(blogId: string): Promise<void> {
    const response = await api.blogs.delete(blogId);
    if (!response.success) {
      throw new Error('Failed to delete blog');
    }
  }

  async deleteStuckTask(taskId: string): Promise<void> {
    // This calls the backend directly to delete stuck generation tasks
    const backendUrl = getBackendUrl();
    
    try {
      let token: string | null = null;
      try {
        token = await authTokenManager.getToken();
      } catch (error) {
        if (error instanceof AuthTokenError && error.status === 401) {
          throw new Error('Authentication required to delete stuck task');
        }
        throw new Error('Failed to get auth token');
      }

      if (!token) {
        throw new Error('Failed to get auth token');
      }

      const response = await fetch(`${backendUrl}/tasks/${taskId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to delete stuck task: ${response.statusText}`);
      }
    } catch (error: any) {
      // Handle SSL certificate errors with helpful guidance
      if (error.message?.includes('ERR_CERT_AUTHORITY_INVALID') || 
          error.message?.includes('Failed to fetch')) {
        logger.error('SSL certificate error when deleting stuck task', {
          message: error.message,
        });
        if (VERBOSE_LOGGING_ENABLED && logger.shouldLog('info')) {
          logger.info('SSL certificate remediation steps', {
            steps: [
              'Visit https://localhost:5000 in your browser',
              'Accept the security warning to trust the certificate',
              'Return to the app and retry the operation',
            ],
          });
        }
        
        throw new Error(
          'SSL certificate not trusted. Please visit https://localhost:5000 in your browser and accept the security certificate, then try again.'
        );
      }
      throw error;
    }
  }

  async getBlogStatus(taskId: string): Promise<{ task_id: string; status: string; progress: number; currentStep?: string }> {
    const backendUrl = getBackendUrl();
    
    try {
      let token: string | null = null;
      try {
        token = await authTokenManager.getToken();
      } catch (error) {
        if (error instanceof AuthTokenError && error.status === 401) {
          throw new Error('Authentication required');
        }
        throw new Error('Failed to get auth token');
      }

      if (!token) {
        throw new Error('Failed to get auth token');
      }

      const response = await fetch(`${backendUrl}/blogs/${taskId}/status`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to get blog status: ${response.statusText}`);
      }

      return await response.json();
    } catch (error: any) {
      logger.error('Error getting blog status', { error });
      throw error;
    }
  }

  async updateBlogCompletion(blogId: string, status: string, content?: string, error?: ErrorInfo, heroImageUrl?: string) {
    // Ensure status is exactly what the API expects
    const validStatus = status === 'completed' ? 'completed' : 'failed';
    
    if (VERBOSE_LOGGING_ENABLED && logger.shouldLog('info')) {
      logger.info('BlogService.updateBlogCompletion invoked', {
        blogId,
        originalStatus: status,
        validStatus,
        contentLength: content?.length || 0,
        hasContent: Boolean(content),
        contentPreview: content ? `${content.substring(0, 100)}...` : null,
        error,
        heroImageUrl,
      });
    }
    
    const response = await api.blogs.updateCompletion(blogId, validStatus, content, error as any, heroImageUrl);
    if (!response.success) {
      throw new Error('Failed to update blog completion status');
    }
    return response.data;
  }

  async generateTitle(instructions: string): Promise<string> {
    try {
      // Call the Next.js API route for title generation
      const response = await fetch('/api/generate-title', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ instructions: instructions.trim() }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate title');
      }

      const data = await response.json();
      return data.title || instructions.substring(0, 50) + '...'; // Fallback to truncated instructions
    } catch (error) {
      logger.error('Title generation error in BlogService.generateTitle', { error });
      // Fallback to a simple truncated version of instructions
      return instructions.substring(0, 50) + '...';
    }
  }

  // ========== Queue Management Methods ==========
  
  async getQueueStatus(): Promise<QueueStatus> {
    const backendUrl = getBackendUrl();
    const token = await authTokenManager.getToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${backendUrl}/queue-status`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch queue status: ${response.statusText}`);
    }

    return await response.json();
  }

  async getGenerationLogs(taskId: string): Promise<GenerationLog[]> {
    const backendUrl = getBackendUrl();
    const token = await authTokenManager.getToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${backendUrl}/generation-logs/${taskId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return []; // Logs have been cleaned up
      }
      throw new Error(`Failed to fetch generation logs: ${response.statusText}`);
    }

    const data = await response.json();
    return data.logs || [];
  }

  async getDraft(taskId: string): Promise<DraftContent | null> {
    const backendUrl = getBackendUrl();
    const token = await authTokenManager.getToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${backendUrl}/draft/${taskId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return null; // No draft available
      }
      throw new Error(`Failed to fetch draft: ${response.statusText}`);
    }

    const data = await response.json();
    return data.draft || null;
  }

  async retryBlog(blogId: string): Promise<{ task_id: string; message: string }> {
    const backendUrl = getBackendUrl();
    const token = await authTokenManager.getToken();
    
    if (!token) {
      throw new Error('Authentication required');
    }

    const response = await fetch(`${backendUrl}/regenerate-blog/${blogId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: response.statusText }));
      throw new Error(error.message || 'Failed to retry blog generation');
    }

    return await response.json();
  }
}

export const blogService = new BlogService();
