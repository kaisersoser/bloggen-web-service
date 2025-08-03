import { useState, useEffect, useRef } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Terminal, Minimize2, Maximize2 } from 'lucide-react';
import { JobState, LogEntry } from '@/types/blog';

interface BlogGenerationViewProps {
  job: JobState | null;
  isGenerating: boolean;
  logs?: LogEntry[];
}

export function BlogGenerationView({ job, isGenerating, logs = [] }: BlogGenerationViewProps) {
  const [consoleCollapsed, setConsoleCollapsed] = useState(false);
  const logsRef = useRef<HTMLDivElement>(null);

  // Auto-scroll logs to bottom
  useEffect(() => {
    if (logsRef.current) {
      logsRef.current.scrollTop = logsRef.current.scrollHeight;
    }
  }, [logs]);

  // Format timestamp for display
  const formatTime = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      });
    } catch {
      return '';
    }
  };

  // Get step color
  const getStepColor = (step: string) => {
    switch (step.toLowerCase()) {
      case 'initialization':
        return 'text-blue-400';
      case 'research':
        return 'text-yellow-400';
      case 'content generation':
        return 'text-green-400';
      case 'fact checking':
        return 'text-purple-400';
      case 'finalization':
        return 'text-cyan-400';
      case 'processing':
        return 'text-gray-400';
      default:
        return 'text-gray-300';
    }
  };

  if (!job && !isGenerating) {
    return (
      <div className="flex-1 flex items-center justify-center text-center py-20">
        <div className="max-w-md">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
            Ready to Generate
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            Click &quot;New Blog&quot; to start creating your blog post
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* CrewAI Console */}
      {(isGenerating || logs.length > 0) && (
        <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center space-x-2">
              <Terminal className="w-4 h-4 text-gray-500 dark:text-gray-400" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">CrewAI Generation Console</span>
              {isGenerating && (
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-xs text-green-600 dark:text-green-400">Live</span>
                </div>
              )}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setConsoleCollapsed(!consoleCollapsed)}
              className="w-8 h-8 p-0"
            >
              {consoleCollapsed ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
            </Button>
          </div>
          
          {!consoleCollapsed && (
            <div 
              ref={logsRef}
              className="h-64 overflow-y-auto bg-black dark:bg-gray-950 p-4 font-mono text-sm"
            >
              {logs.length === 0 && isGenerating ? (
                <div className="text-gray-400">
                  <span className="animate-pulse">Initializing CrewAI workflow...</span>
                </div>
              ) : (
                <div className="space-y-1">
                  {logs.map((log, index) => (
                    <div key={index} className="flex items-start space-x-3">
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
                  ))}
                  {isGenerating && (
                    <div className="flex items-start space-x-3">
                      <span className="text-gray-500 text-xs mt-0.5 w-20 flex-shrink-0">
                        {formatTime(new Date().toISOString())}
                      </span>
                      <span className="text-blue-400 text-xs font-semibold w-24 flex-shrink-0">
                        [SYSTEM]
                      </span>
                      <span className="text-gray-300 dark:text-gray-400">
                        <span className="animate-pulse">Processing...</span>
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Blog Content Area */}
      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto p-6">
          {/* Generation Status */}
          {job && job.status === 'in_progress' && (
            <div className="mb-6 text-center">
              <div className="inline-flex items-center gap-3 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-4 py-2 rounded-full">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 dark:border-blue-400 border-t-transparent"></div>
                <span className="text-sm font-medium">{job.currentStep}</span>
              </div>
            </div>
          )}

          {/* Error Display */}
          {job?.error && (
            <Card className="mb-6 p-6 border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/30">
              <h4 className="font-semibold text-red-800 dark:text-red-200 mb-2">Generation Failed</h4>
              <p className="text-sm text-red-700 dark:text-red-300 mb-4">{job.error.user_message}</p>
              {job.error.suggestions && job.error.suggestions.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-red-800 dark:text-red-200 mb-2">Suggestions:</p>
                  <ul className="text-sm text-red-700 dark:text-red-300 list-disc list-inside space-y-1">
                    {job.error.suggestions.map((suggestion, index) => (
                      <li key={index}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          )}

          {/* Generation Complete Message */}
          {job?.status === 'completed' && (
            <Card className="p-6 bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800">
              <div className="flex items-center justify-center text-center">
                <div>
                  <div className="flex items-center justify-center w-12 h-12 mx-auto mb-4 bg-green-100 dark:bg-green-800 rounded-full">
                    <svg className="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-semibold text-green-800 dark:text-green-200 mb-2">
                    Blog Generated Successfully!
                  </h3>
                  <p className="text-green-700 dark:text-green-300 text-sm">
                    Your blog post &quot;{job.topic}&quot; has been generated and is now available in the Blog History sidebar.
                    The blog will automatically open in a modal window for you to review.
                  </p>
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
