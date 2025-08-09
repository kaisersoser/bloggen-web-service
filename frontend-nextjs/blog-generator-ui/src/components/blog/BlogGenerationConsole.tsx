import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Terminal, Minimize2, Maximize2 } from 'lucide-react';
import { LogEntry } from '@/types/blog';
import { STEP_COLOR_MAP } from '@/config/constants';

interface BlogGenerationConsoleProps {
  isGenerating: boolean;
  logs: LogEntry[];
}

export function BlogGenerationConsole({ isGenerating, logs }: BlogGenerationConsoleProps) {
  const [consoleCollapsed, setConsoleCollapsed] = useState(false);
  const logsRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (logsRef.current) logsRef.current.scrollTop = logsRef.current.scrollHeight; }, [logs]);

  const formatTime = (timestamp: string) => { try { return new Date(timestamp).toLocaleTimeString('en-US',{hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'});} catch {return '';} };
  const getStepColor = (step: string) => STEP_COLOR_MAP[step.toLowerCase()] || 'text-gray-300';

  if (!isGenerating && logs.length === 0) return null;

  return (
    <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">CrewAI Generation Console</span>
          {isGenerating && (
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-xs text-green-600 dark:text-green-400">Live</span>
            </div>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={() => setConsoleCollapsed(!consoleCollapsed)} className="w-8 h-8 p-0">
          {consoleCollapsed ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
        </Button>
      </div>
      {!consoleCollapsed && (
        <div ref={logsRef} className="h-64 overflow-y-auto bg-black dark:bg-gray-950 p-4 font-mono text-sm">
          {logs.length === 0 && isGenerating ? (
            <div className="text-gray-400"><span className="animate-pulse">Initializing CrewAI workflow...</span></div>
          ) : (
            <div className="space-y-1">
              {logs.map((log, idx) => (
                <div key={idx} className="flex items-start space-x-3">
                  <span className="text-gray-500 text-xs mt-0.5 w-20 flex-shrink-0">{formatTime(log.timestamp)}</span>
                  <span className={`text-xs font-semibold w-24 flex-shrink-0 ${getStepColor(log.step)}`}>[{log.step}]</span>
                  <span className="text-gray-300 dark:text-gray-400 leading-relaxed">{log.message}</span>
                </div>
              ))}
              {isGenerating && (
                <div className="flex items-start space-x-3">
                  <span className="text-gray-500 text-xs mt-0.5 w-20 flex-shrink-0">{formatTime(new Date().toISOString())}</span>
                  <span className="text-blue-400 text-xs font-semibold w-24 flex-shrink-0">[SYSTEM]</span>
                  <span className="text-gray-300 dark:text-gray-400"><span className="animate-pulse">Processing...</span></span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
