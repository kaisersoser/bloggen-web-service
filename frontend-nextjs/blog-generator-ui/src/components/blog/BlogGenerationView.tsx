import { Card } from '@/components/ui/card';
import { JobState, LogEntry, StreamingContentState } from '@/types/blog';
import { BlogGenerationConsole } from '@/components/blog/BlogGenerationConsole';
import { LiveContentPreview } from '@/components/blog/LiveContentPreview';

interface BlogGenerationViewProps {
  job: JobState | null;
  isGenerating: boolean;
  logs?: LogEntry[];
  streamingContent?: StreamingContentState;
  showStreamingPreview?: boolean;
}

export function BlogGenerationView({ 
  job, 
  isGenerating, 
  logs = [],
  streamingContent,
  showStreamingPreview = false
}: BlogGenerationViewProps) {

  // Show console if generating OR if there's any job (in progress, completed, or failed)
  const shouldShowConsole = isGenerating || job;

  if (!shouldShowConsole) {
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
  <BlogGenerationConsole 
    isGenerating={isGenerating} 
    logs={logs} 
    generationStartTime={job?.createdAt}
  />

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

          {/* Phase 4 Progressive Content Streaming */}
          {showStreamingPreview && streamingContent && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
                <div className="animate-pulse h-2 w-2 bg-green-500 rounded-full"></div>
                Live Content Preview
              </h3>
              <LiveContentPreview 
                streamingContent={streamingContent}
                className="animate-fade-in"
              />
            </div>
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
