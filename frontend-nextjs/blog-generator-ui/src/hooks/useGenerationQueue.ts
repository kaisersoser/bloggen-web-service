import { useState, useEffect, useCallback } from 'react';
import { QueueStatus } from '@/types/queue';
import { blogService } from '@/lib/services/blog';
import { logger } from '@/lib/logger';

export function useGenerationQueue(autoRefresh = true, refreshInterval = 5000) {
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchQueueStatus = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const status = await blogService.getQueueStatus();
      setQueueStatus(status);
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch queue status';
      setError(errorMessage);
      logger.error('Error fetching queue status', { error: err });
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Auto-refresh queue status
  useEffect(() => {
    if (!autoRefresh) return;

    fetchQueueStatus();
    const interval = setInterval(fetchQueueStatus, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, fetchQueueStatus]);

  return {
    queueStatus,
    isLoading,
    error,
    refresh: fetchQueueStatus,
  };
}
