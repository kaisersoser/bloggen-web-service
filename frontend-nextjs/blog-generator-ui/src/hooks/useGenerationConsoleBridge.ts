"use client";

import { useCallback, useEffect, useMemo, useRef } from 'react';
import { useConsoleMessages } from '@/hooks/useConsoleMessages';
import { useStreamingContent } from '@/hooks/useStreamingContent';
import { logger } from '@/lib/logger';
import { VERBOSE_LOGGING_ENABLED } from '@/lib/logger/env';
import type { LogEntry } from '@/types/blog';

interface UseGenerationConsoleBridgeProps {
  taskLogs: Record<string, LogEntry[]> | undefined;
  currentJobId: string | null;
  isGenerating: boolean;
  clearTaskLogs?: () => void;
}

const MAX_TYPEWRITER_DELAY = 3000;
const MIN_TYPEWRITER_DELAY = 800;
const BASE_DELAY_OFFSET = 600;
const CHARACTER_RATE = 30;

export function useGenerationConsoleBridge({
  taskLogs,
  currentJobId,
  isGenerating,
  clearTaskLogs,
}: UseGenerationConsoleBridgeProps) {
  const {
    messages,
    addMessage,
    clearMessages,
    formatTimestamp,
    getMessageIcon,
    getMessageColorClass,
    messagesEndRef,
    consoleContainerRef,
  } = useConsoleMessages();
  const { streamingContent } = useStreamingContent();

  const lastProcessedIndex = useRef<Record<string, number>>({});
  const processingQueue = useRef<Array<{ log: LogEntry; index: number }>>([]);
  const isProcessingQueue = useRef(false);
  const isBlogCompleted = useRef(false);

  const shouldLogVerbose = useCallback(
    () => VERBOSE_LOGGING_ENABLED && logger.shouldLog('info'),
    []
  );

  const resetQueueState = useCallback(() => {
    processingQueue.current = [];
    isProcessingQueue.current = false;
    isBlogCompleted.current = false;
    lastProcessedIndex.current = {};
  }, []);

  const prepareForNewGeneration = useCallback(() => {
    if (shouldLogVerbose()) {
      logger.info('🧹 Preparing console for new blog generation request');
    }
    clearMessages();
    if (clearTaskLogs) {
      clearTaskLogs();
      if (shouldLogVerbose()) {
        logger.info('🧹 Task logs cleared for new blog generation');
      }
    }
    resetQueueState();
  }, [clearMessages, clearTaskLogs, resetQueueState, shouldLogVerbose]);

  const processMessageQueue = useCallback(async () => {
    if (isProcessingQueue.current || processingQueue.current.length === 0) {
      return;
    }

    isProcessingQueue.current = true;

    while (processingQueue.current.length > 0) {
      if (isBlogCompleted.current) {
        if (shouldLogVerbose()) {
          logger.info('🛑 Blog completed during typewriter processing, fast-flush pending messages');
        }
        break;
      }

      const { log, index } = processingQueue.current.shift()!;

      if (shouldLogVerbose()) {
        logger.info(`➕ Rendering console message ${index + 1}`, log);
      }

      addMessage(
        log.step || 'info',
        log.message,
        { progress: log.progress, timestamp: log.timestamp },
        'info'
      );

      if (processingQueue.current.length > 0 && !isBlogCompleted.current) {
        const messageLength = log.message?.length ?? 0;
        const dynamicDelay =
          (messageLength / CHARACTER_RATE) * 1000 + BASE_DELAY_OFFSET;
        const typewriterDelay = Math.max(
          MIN_TYPEWRITER_DELAY,
          Math.min(MAX_TYPEWRITER_DELAY, dynamicDelay)
        );

        if (shouldLogVerbose()) {
          logger.info('⏰ Typewriter delay calculated', {
            messageLength,
            typewriterDelay,
          });
        }

        await new Promise((resolve) => setTimeout(resolve, typewriterDelay));
      }
    }

    isProcessingQueue.current = false;
  }, [addMessage, shouldLogVerbose]);

  useEffect(() => {
    if (!currentJobId) {
      return;
    }

    const logs = taskLogs?.[currentJobId];
    if (!logs || logs.length === 0) {
      return;
    }

    const hasCompletionMessage = logs.some((log) => {
      const message = log.message?.toLowerCase() ?? '';
      const step = log.step?.toLowerCase() ?? '';
      return (
        message.includes('blog generation complete') ||
        message.includes('finalization complete') ||
        message.includes('content cleaning completed') ||
        step.includes('complete')
      );
    });

    const shouldFlush =
      (!isGenerating && Boolean(currentJobId)) || hasCompletionMessage;

    if (shouldFlush && !isBlogCompleted.current) {
      if (shouldLogVerbose()) {
        logger.info('🎯 Blog completion detected; flushing pending console messages');
      }
      isBlogCompleted.current = true;

      while (processingQueue.current.length > 0) {
        const { log, index } = processingQueue.current.shift()!;
        if (shouldLogVerbose()) {
          logger.info(`⚡ Fast-flushing message ${index + 1}`, log);
        }
        addMessage(
          log.step || 'info',
          log.message,
          { progress: log.progress, timestamp: log.timestamp },
          'info'
        );
      }
      isProcessingQueue.current = false;
    }

    if (isGenerating && isBlogCompleted.current) {
      if (shouldLogVerbose()) {
        logger.info('🔄 New generation detected; resetting completion state');
      }
      isBlogCompleted.current = false;
    }
  }, [
    addMessage,
    currentJobId,
    isGenerating,
    shouldLogVerbose,
    taskLogs,
  ]);

  useEffect(() => {
    if (!currentJobId) {
      return;
    }

    const logs = taskLogs?.[currentJobId];
    if (!logs || logs.length === 0) {
      return;
    }

    const lastIndex = lastProcessedIndex.current[currentJobId] ?? 0;

    if (logs.length <= lastIndex) {
      return;
    }

    const newLogs = logs.slice(lastIndex);

    if (shouldLogVerbose()) {
      logger.info('📊 Queueing new console logs', {
        currentJobId,
        newLogsCount: newLogs.length,
        startingIndex: lastIndex,
      });
    }

    newLogs.forEach((log, index) => {
      processingQueue.current.push({ log, index: lastIndex + index });
    });

    lastProcessedIndex.current[currentJobId] = logs.length;

    if (isBlogCompleted.current) {
      while (processingQueue.current.length > 0) {
        const { log, index } = processingQueue.current.shift()!;
        if (shouldLogVerbose()) {
          logger.info(`⚡ Immediate-add message ${index + 1}`, log);
        }
        addMessage(
          log.step || 'info',
          log.message,
          { progress: log.progress, timestamp: log.timestamp },
          'info'
        );
      }
      isProcessingQueue.current = false;
    } else {
      void processMessageQueue();
    }
  }, [addMessage, currentJobId, processMessageQueue, shouldLogVerbose, taskLogs]);

  useEffect(() => {
    if (!currentJobId) {
      return;
    }

    if (!lastProcessedIndex.current[currentJobId]) {
      lastProcessedIndex.current[currentJobId] = 0;
      processingQueue.current = [];
      isProcessingQueue.current = false;
      isBlogCompleted.current = false;
    }
  }, [currentJobId]);

  const consoleHelpers = useMemo(
    () => ({
      formatTimestamp,
      getMessageIcon,
      getMessageColorClass,
      messagesEndRef,
      consoleContainerRef,
    }),
    [
      consoleContainerRef,
      formatTimestamp,
      getMessageColorClass,
      getMessageIcon,
      messagesEndRef,
    ]
  );

  return {
    messages,
    streamingContent,
    clearMessages,
    prepareForNewGeneration,
    ...consoleHelpers,
  } as const;
}
