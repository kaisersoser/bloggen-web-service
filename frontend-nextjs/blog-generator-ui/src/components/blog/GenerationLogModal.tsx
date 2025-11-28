"use client";

import React, { useEffect, useRef, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Download, RefreshCw } from 'lucide-react';
import { GenerationLog } from '@/types/queue';
import { LogEntry } from '@/types/blog';
import { format } from 'date-fns';

interface GenerationLogModalProps {
  isOpen: boolean;
  onClose: () => void;
  taskId: string;
  logs: GenerationLog[];
  isLoading?: boolean;
  isLive?: boolean; // Whether logs are still being generated
  onRefresh?: () => void;
}

export const GenerationLogModal: React.FC<GenerationLogModalProps> = ({
  isOpen,
  onClose,
  taskId,
  logs,
  isLoading = false,
  isLive = false,
  onRefresh,
}) => {
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Convert fetched logs to LogEntry format for consistent display
  const displayLogs: LogEntry[] = logs.map(log => ({
    timestamp: log.timestamp,
    step: log.step,
    message: log.message,
    progress: log.progress,
    level: log.level
  }));

  // Debug: Log what we're receiving
  useEffect(() => {
    console.log('[MODAL RENDER]', {
      taskId,
      isOpen,
      isLive,
      logsReceived: logs.length,
      displayLogsCount: displayLogs.length,
      firstLog: logs[0],
      lastLog: logs[logs.length - 1]
    });
  }, [taskId, isOpen, isLive, logs.length, displayLogs.length, logs]);

  // Filter out connection status messages that aren't real logs
  const filteredLogs = displayLogs.filter(log => {
    if (log.step === 'connection' || log.message === 'Live updates connected' || log.message === 'Connection closed') {
      return false;
    }
    return true;
  });

  // Auto-scroll to bottom when new logs arrive (like Console does)
  useEffect(() => {
    if (autoScroll && scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [filteredLogs, autoScroll]);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const isAtBottom = Math.abs(target.scrollHeight - target.scrollTop - target.clientHeight) < 10;
    setAutoScroll(isAtBottom);
  };

  const downloadLogs = () => {
    const logText = filteredLogs
      .map(log => `[${format(new Date(log.timestamp), 'yyyy-MM-dd HH:mm:ss')}] ${log.step} (${log.progress}%): ${log.message}`)
      .join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `generation-logs-${taskId}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getLevelColor = (level?: string) => {
    switch (level) {
      case 'success':
        return 'text-green-600 dark:text-green-400';
      case 'error':
        return 'text-red-600 dark:text-red-400';
      case 'warning':
        return 'text-yellow-600 dark:text-yellow-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const _getLevelBg = (level?: string) => {
    switch (level) {
      case 'success':
        return 'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800';
      case 'error':
        return 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800';
      case 'warning':
        return 'bg-yellow-50 dark:bg-yellow-950/30 border-yellow-200 dark:border-yellow-800';
      default:
        return 'bg-gray-50 dark:bg-gray-950/30 border-gray-200 dark:border-gray-800';
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col">
        <DialogHeader className="flex-shrink-0 pb-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1 min-w-0">
              <DialogTitle className="truncate">Generation Logs</DialogTitle>
              <DialogDescription className="truncate">
                Real-time logs for task {taskId.slice(0, 8)}...
                {isLive && (
                  <span className="ml-2 inline-flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400">
                    <span className="relative flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                    </span>
                    Live
                  </span>
                )}
              </DialogDescription>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              {onRefresh && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onRefresh}
                  disabled={isLoading}
                  className="gap-2"
                >
                  <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={downloadLogs}
                disabled={filteredLogs.length === 0}
                className="gap-2"
              >
                <Download className="h-4 w-4" />
                Download
              </Button>
            </div>
          </div>
        </DialogHeader>

        {isLoading && filteredLogs.length === 0 ? (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">Loading logs...</p>
            </div>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <p className="text-sm text-muted-foreground">No logs available</p>
              <p className="text-xs text-muted-foreground mt-1">
                {isLive ? 'Waiting for generation to start...' : 'Logs may have been cleaned up after completion'}
              </p>
            </div>
          </div>
        ) : (
          <div 
            ref={scrollAreaRef}
            onScroll={handleScroll}
            className="overflow-y-auto h-[60vh] bg-black dark:bg-gray-950 rounded-md p-4 font-mono text-sm relative"
          >
            <div className="space-y-1">
              {filteredLogs.map((log, index) => (
                <div
                  key={`${log.timestamp}-${index}`}
                  className="flex items-start gap-3"
                >
                  <span className="text-gray-500 text-xs mt-0.5 w-20 flex-shrink-0">
                    {format(new Date(log.timestamp), 'HH:mm:ss')}
                  </span>
                  <span className={`text-xs font-semibold w-32 flex-shrink-0 ${getLevelColor(log.level)}`}>
                    [{log.step}]
                  </span>
                  <span className="text-gray-300 dark:text-gray-400 leading-relaxed flex-1">
                    {log.message}
                  </span>
                  <span className="text-xs font-medium text-gray-500 whitespace-nowrap flex-shrink-0">
                    {log.progress}%
                  </span>
                </div>
              ))}
              {isLive && (
                <div className="flex items-start gap-3">
                  <span className="text-gray-500 text-xs mt-0.5 w-20 flex-shrink-0">
                    {format(new Date(), 'HH:mm:ss')}
                  </span>
                  <span className="text-blue-400 text-xs font-semibold w-32 flex-shrink-0">
                    [SYSTEM]
                  </span>
                  <span className="text-gray-300 dark:text-gray-400">
                    <span className="animate-pulse">Processing...</span>
                  </span>
                </div>
              )}
            </div>
            {!autoScroll && isLive && (
              <div className="sticky bottom-4 left-1/2 transform -translate-x-1/2 w-fit mx-auto mt-4">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setAutoScroll(true);
                    if (scrollAreaRef.current) {
                      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
                    }
                  }}
                  className="shadow-lg"
                >
                  Scroll to bottom
                </Button>
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default GenerationLogModal;
