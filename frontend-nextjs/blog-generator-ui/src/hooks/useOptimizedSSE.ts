// QUICK FIX 2: Debounced SSE Console Updates
// src/hooks/useOptimizedSSE.ts

import { useCallback, useRef } from 'react';
import { LogEntry } from '@/types/blog';

export function useOptimizedSSE() {
  const logBufferRef = useRef<LogEntry[]>([]);
  const updateTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const batchUpdateLogs = useCallback((logs: LogEntry[], onUpdate: (logs: LogEntry[]) => void) => {
    // Add new logs to buffer
    logBufferRef.current = [...logBufferRef.current, ...logs];

    // Clear existing timeout
    if (updateTimeoutRef.current) {
      clearTimeout(updateTimeoutRef.current);
    }

    // Batch updates every 100ms to reduce DOM thrashing
    updateTimeoutRef.current = setTimeout(() => {
      onUpdate([...logBufferRef.current]);
      logBufferRef.current = [];
    }, 100);
  }, []);

  const optimizedScrollToBottom = useCallback((element: HTMLElement | null) => {
    if (!element) return;
    
    // Use requestAnimationFrame for smooth scrolling
    requestAnimationFrame(() => {
      element.scrollTop = element.scrollHeight;
    });
  }, []);

  return { batchUpdateLogs, optimizedScrollToBottom };
}
