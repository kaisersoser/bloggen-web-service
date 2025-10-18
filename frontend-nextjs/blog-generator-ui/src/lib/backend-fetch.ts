/**
 * Backend fetch utility with custom HTTPS agent configuration
 * for development environments using self-signed certificates.
 * 
 * Note: NODE_TLS_REJECT_UNAUTHORIZED is set to '0' by dev-dynamic.js for development
 */

import { serverLogger } from '@/lib/logger/server';
import { VERBOSE_LOGGING_ENABLED } from '@/lib/logger/env';

interface BackendFetchOptions extends RequestInit {
  timeout?: number;
}

/**
 * Fetch wrapper for backend API calls that handles timeouts
 * SSL certificate handling is managed by the NODE_TLS_REJECT_UNAUTHORIZED environment variable
 * set during development startup in dev-dynamic.js
 */
export async function backendFetch(
  endpoint: string, 
  options: BackendFetchOptions = {}
): Promise<Response> {
  // Priority: API_BASE_URL (server-side) > NEXT_PUBLIC_API_URL (client + server) > localhost fallback
  const API_BASE_URL = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'https://localhost:5001';
  const { timeout = 15000, ...fetchOptions } = options;
  
  // Debug logging
  if (VERBOSE_LOGGING_ENABLED) {
    serverLogger.info('backendFetch invoked', {
      endpoint,
      url: `${API_BASE_URL}${endpoint}`,
      timeout,
      nodeTlsRejectUnauthorized: process.env.NODE_TLS_REJECT_UNAUTHORIZED,
      hasAuthHeader: Boolean(fetchOptions.headers && 'Authorization' in fetchOptions.headers),
    });
  }
  
  // Create abort controller for timeout handling
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...fetchOptions,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    if (VERBOSE_LOGGING_ENABLED) {
      serverLogger.info('backendFetch response received', {
        status: response.status,
        ok: response.ok,
        url: response.url,
      });
    }
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    
    // Enhanced error logging for SSL certificate issues
    serverLogger.error('backendFetch error details', {
      message: error instanceof Error ? error.message : String(error),
      code: error instanceof Error && 'code' in error ? (error as any).code : undefined,
      cause: error instanceof Error && 'cause' in error ? (error as any).cause : undefined,
      errorType: typeof error,
      endpoint,
      url: `${API_BASE_URL}${endpoint}`,
      nodeTlsRejectUnauthorized: process.env.NODE_TLS_REJECT_UNAUTHORIZED,
    });
    
    // Log SSL-related errors for debugging
    if (error instanceof Error && error.message.includes('self-signed certificate')) {
      serverLogger.error('SSL certificate error detected in backendFetch', {
        nodeTlsRejectUnauthorized: process.env.NODE_TLS_REJECT_UNAUTHORIZED,
        apiBaseUrl: API_BASE_URL,
      });
    }
    
    throw error;
  }
}

/**
 * Helper function to make authenticated requests to the backend
 */
export async function authenticatedBackendFetch(
  endpoint: string,
  token: string,
  options: BackendFetchOptions = {}
): Promise<Response> {
  return backendFetch(endpoint, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
}
