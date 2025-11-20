import { useState, useEffect, useCallback, useRef } from 'react';
import { GenerationLog } from '@/types/queue';
import { blogService } from '@/lib/services/blog';
import { logger } from '@/lib/logger';

export function useGenerationLogs(taskId: string | null, autoRefresh = true, refreshInterval = 2000) {
  const [logs, setLogs] = useState<GenerationLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchLogs = useCallback(async () => {
    if (!taskId) {
      setLogs([]);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const fetchedLogs = await blogService.getGenerationLogs(taskId);
      setLogs(fetchedLogs);
      
      // If logs are empty (cleaned up), stop auto-refresh
      if (fetchedLogs.length === 0 && intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to fetch generation logs';
      setError(errorMessage);
      logger.error('Error fetching generation logs', { taskId, error: err });
      
      // Stop auto-refresh on error
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    } finally {
      setIsLoading(false);
    }
  }, [taskId]);

  // Auto-refresh logs
  useEffect(() => {
    if (!autoRefresh || !taskId) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    fetchLogs(); // Initial fetch
    intervalRef.current = setInterval(fetchLogs, refreshInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [taskId, autoRefresh, refreshInterval, fetchLogs]);

  const stopAutoRefresh = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  return {
    logs,
    isLoading,
    error,
    refresh: fetchLogs,
    stopAutoRefresh,
  };
}
