import { useState, useEffect, useCallback, useRef } from 'react';
import { DraftContent } from '@/types/queue';
import { blogService } from '@/lib/services/blog';
import { logger } from '@/lib/logger';

export function useDraftContent(taskId: string | null, autoRefresh = true, refreshInterval = 3000) {
  const [draft, setDraft] = useState<DraftContent | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchDraft = useCallback(async () => {
    if (!taskId) {
      setDraft(null);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const fetchedDraft = await blogService.getDraft(taskId);
      setDraft(fetchedDraft);
      
      // If draft is null (cleaned up or completed), stop auto-refresh
      if (!fetchedDraft && intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch draft content';
      setError(errorMessage);
      logger.error('Error fetching draft content', { taskId, error: err });
      
      // Stop auto-refresh on error
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  // Auto-refresh draft
  useEffect(() => {
    if (!autoRefresh || !taskId) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    fetchDraft(); // Initial fetch
    intervalRef.current = setInterval(fetchDraft, refreshInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [taskId, autoRefresh, refreshInterval, fetchDraft]);

  const stopAutoRefresh = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  return {
    draft,
    isLoading,
    error,
    refresh: fetchDraft,
    stopAutoRefresh,
  };
}
