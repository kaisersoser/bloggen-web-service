// QUICK FIX 4: Optimized Console Component
// src/components/blog/OptimizedBlogConsole.tsx

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Terminal, Minimize2, Maximize2 } from 'lucide-react';
import { LogEntry } from '@/types/blog';

interface OptimizedBlogConsoleProps {
  isGenerating: boolean;
  logs: LogEntry[];
}

export const OptimizedBlogConsole = React.memo(function OptimizedBlogConsole({ 
  isGenerating, 
  logs 
}: OptimizedBlogConsoleProps) {
  const [consoleCollapsed, setConsoleCollapsed] = useState(false);
  const logsRef = useRef<HTMLDivElement>(null);
  const shouldAutoScrollRef = useRef(true);

  // Optimized scroll behavior
  const scrollToBottom = useCallback(() => {
    if (!logsRef.current || !shouldAutoScrollRef.current) return;
    
    requestAnimationFrame(() => {
      if (logsRef.current) {
        logsRef.current.scrollTop = logsRef.current.scrollHeight;
      }
    });
  }, []);

  // Check if user is manually scrolling
  const handleScroll = useCallback(() => {
    if (!logsRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = logsRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 10;
    shouldAutoScrollRef.current = isAtBottom;
  }, []);

  // Throttled scroll to bottom
  useEffect(() => {
    if (logs.length > 0) {
      scrollToBottom();
    }
  }, [logs.length, scrollToBottom]);

  // Memoized log rendering
  const renderedLogs = React.useMemo(() => {
    return logs.map((log, idx) => (
      <LogLine key={`${log.timestamp}-${idx}`} log={log} />
    ));
  }, [logs]);

  if (!isGenerating && logs.length === 0) return null;

  return (
    <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
      <ConsoleHeader 
        isGenerating={isGenerating}
        consoleCollapsed={consoleCollapsed}
        onToggleCollapse={() => setConsoleCollapsed(!consoleCollapsed)}
      />
      
      {!consoleCollapsed && (
        <div 
          ref={logsRef}
          onScroll={handleScroll}
          className="h-64 overflow-y-auto bg-black dark:bg-gray-950 p-4 font-mono text-sm"
        >
          {logs.length === 0 && isGenerating ? (
            <div className="text-gray-400">
              <span className="animate-pulse">Initializing CrewAI workflow...</span>
            </div>
          ) : (
            <div className="space-y-1">
              {renderedLogs}
              {isGenerating && <GeneratingIndicator />}
            </div>
          )}
        </div>
      )}
    </div>
  );
});

// Memoized sub-components for better performance
const ConsoleHeader = React.memo(function ConsoleHeader({ 
  isGenerating, 
  consoleCollapsed, 
  onToggleCollapse 
}: {
  isGenerating: boolean;
  consoleCollapsed: boolean;
  onToggleCollapse: () => void;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700">
      <div className="flex items-center space-x-2">
        <Terminal className="w-4 h-4 text-gray-500 dark:text-gray-400" />
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          CrewAI Generation Console
        </span>
        {isGenerating && <LiveIndicator />}
      </div>
      <Button 
        variant="ghost" 
        size="sm" 
        onClick={onToggleCollapse} 
        className="w-8 h-8 p-0"
      >
        {consoleCollapsed ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
      </Button>
    </div>
  );
});

const LiveIndicator = React.memo(function LiveIndicator() {
  return (
    <div className="flex items-center space-x-2">
      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
      <span className="text-xs text-green-600 dark:text-green-400">Live</span>
    </div>
  );
});

const LogLine = React.memo(function LogLine({ log }: { log: LogEntry }) {
  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return '';
    }
  };

  const getStepColor = (step: string) => {
    const colorMap: Record<string, string> = {
      'research': 'text-blue-400',
      'generation': 'text-green-400',
      'fact-check': 'text-yellow-400',
      'finalization': 'text-purple-400',
      'system': 'text-cyan-400',
      'error': 'text-red-400'
    };
    return colorMap[step.toLowerCase()] || 'text-gray-300';
  };

  return (
    <div className="flex items-start space-x-3">
      <span className="text-gray-500 text-xs mt-0.5 w-20 flex-shrink-0">
        {formatTime(log.timestamp)}
      </span>
      <span className={`text-xs font-semibold w-24 flex-shrink-0 ${getStepColor(log.step)}`}>
        [{log.step}]
      </span>
      <span className="text-gray-300 dark:text-gray-400 leading-relaxed">
        {log.message}
      </span>
    </div>
  );
});

const GeneratingIndicator = React.memo(function GeneratingIndicator() {
  return (
    <div className="flex items-start space-x-3">
      <span className="text-gray-500 text-xs mt-0.5 w-20 flex-shrink-0">
        {new Date().toLocaleTimeString('en-US', {
          hour12: false,
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        })}
      </span>
      <span className="text-blue-400 text-xs font-semibold w-24 flex-shrink-0">[SYSTEM]</span>
      <span className="text-gray-300 dark:text-gray-400">
        <span className="animate-pulse">Processing...</span>
      </span>
    </div>
  );
});
