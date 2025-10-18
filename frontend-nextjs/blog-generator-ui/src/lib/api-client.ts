/**
 * Centralized API Client for Blog Generation Service
 * 
 * Provides standardized HTTP client functionality with consistent error handling,
 * authentication, and request/response patterns across the frontend application.
 */

import { logger } from '@/lib/logger';
import { authTokenManager, AuthTokenError } from '@/lib/authTokenManager';

interface ApiConfig {
  baseUrl?: string;
  timeout?: number;
  retries?: number;
}

interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
  success: boolean;
}

interface RequestOptions extends RequestInit {
  timeout?: number;
  retries?: number;
}

class ApiError extends Error {
  public status: number;
  public code?: string;
  public details?: any;

  constructor(message: string, status: number, code?: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

class ApiClient {
  private baseUrl: string;
  private timeout: number;
  private retries: number;

  constructor(config: ApiConfig = {}) {
    this.baseUrl = config.baseUrl || '';
    this.timeout = config.timeout || 30000;
    this.retries = config.retries || 3;
  }

  /**
   * Get authentication token for API requests
   */
  private async getAuthToken(): Promise<string | null> {
    try {
      return await authTokenManager.getToken();
    } catch (error) {
      if (error instanceof AuthTokenError && error.status === 401) {
        logger.warn('User not authenticated while requesting auth token');
        throw new Error(error.message || 'Authentication required');
      }
      return null;
    }
  }

  /**
   * Create request headers with common defaults
   */
  private async createHeaders(customHeaders: HeadersInit = {}): Promise<Headers> {
    const headers = new Headers({
      'Content-Type': 'application/json',
      ...customHeaders,
    });

    // Add auth token if available
    const token = await this.getAuthToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    return headers;
  }

  /**
   * Handle API response with standardized error processing
   */
  private async handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
    const contentType = response.headers.get('content-type');
    const isJson = contentType?.includes('application/json');

    try {
      const data = isJson ? await response.json() : await response.text();

      if (!response.ok) {
        const errorMessage = data?.message || data?.error || `HTTP ${response.status}`;
        throw new ApiError(
          errorMessage,
          response.status,
          data?.error_code,
          data?.details
        );
      }

      return {
        data,
        success: true,
      };
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }

      throw new ApiError(
        `Failed to parse response: ${error instanceof Error ? error.message : 'Unknown error'}`,
        response.status
      );
    }
  }

  /**
   * Make HTTP request with retry logic and timeout
   */
  private async makeRequest<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    const { timeout = this.timeout, retries = this.retries, ...fetchOptions } = options;
    const url = `${this.baseUrl}${endpoint}`;

    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        const headers = await this.createHeaders(fetchOptions.headers);

        const response = await fetch(url, {
          ...fetchOptions,
          headers,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);
        return await this.handleResponse<T>(response);

      } catch (error) {
        // Don't retry on client errors (4xx) or auth issues
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          throw error;
        }

        // Don't retry on abort (timeout)
        if (error && typeof error === 'object' && 'name' in error && error.name === 'AbortError') {
          throw new ApiError('Request timeout', 408);
        }

        // Last attempt - throw the error
        if (attempt === retries) {
          if (error instanceof ApiError) {
            throw error;
          }
          const message = error instanceof Error ? error.message : 'Unknown error';
          throw new ApiError(`Network error: ${message}`, 0);
        }

        // Wait before retrying (exponential backoff)
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
      }
    }

    throw new ApiError('Max retries exceeded', 0);
  }

  /**
   * GET request
   */
  async get<T>(endpoint: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(endpoint, {
      ...options,
      method: 'GET',
    });
  }

  /**
   * POST request
   */
  async post<T>(
    endpoint: string,
    data?: any,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PUT request
   */
  async put<T>(
    endpoint: string,
    data?: any,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * DELETE request
   */
  async delete<T>(endpoint: string, options: RequestOptions = {}): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(endpoint, {
      ...options,
      method: 'DELETE',
    });
  }

  /**
   * PATCH request
   */
  async patch<T>(
    endpoint: string,
    data?: any,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    return this.makeRequest<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }
}

// Create default client instance
export const apiClient = new ApiClient();

// Export types for use in other components
export type { ApiResponse, ApiConfig, RequestOptions };
export { ApiError, ApiClient };

// Convenience functions for common patterns
export const api = {
  // Blog operations
  blogs: {
    list: () => apiClient.get<{ blogs: any[] }>('/api/blogs'),
    generateTaskId: () => apiClient.post<{ task_id: string }>('/api/generate-task-id'),
    generate: (topic: string, instructions?: string, taskId?: string) =>
      apiClient.post('/api/generate-blog', { topic: topic.trim(), instructions: instructions?.trim(), task_id: taskId }),
    delete: (blogId: string) => apiClient.delete(`/api/blogs/delete?id=${blogId}`),
    updateCompletion: (blogId: string, status: string, content?: string, error?: string, heroImageUrl?: string) =>
      apiClient.post('/api/blog-complete', { blog_id: blogId, status, content, error, hero_image_url: heroImageUrl }),
  },

  // Task operations  
  tasks: {
    getStatus: (taskId: string) => apiClient.get(`/api/tasks/${taskId}`),
    getActiveTasks: () => apiClient.get('/api/tasks/active'),
  },

  // Title operations
  title: {
    generate: (instructions: string) =>
      apiClient.post<{ title: string }>('/api/generate-title', { instructions: instructions.trim() }),
  },

  // User operations
  user: {
    stats: () => apiClient.get('/api/user/stats'),
  },

  // Admin operations
  admin: {
    analytics: (days: number = 30) => apiClient.get(`/api/admin/audit/analytics?days=${days}`),
  },
};
