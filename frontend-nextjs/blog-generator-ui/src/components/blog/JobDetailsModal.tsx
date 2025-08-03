import { useState, useRef, useEffect } from 'react';
import Image from 'next/image';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { JobState } from '@/types/blog';

interface JobDetailsModalProps {
  job: JobState;
  onClose: () => void;
}

export function JobDetailsModal({ job, onClose }: JobDetailsModalProps) {
  const [showLogs, setShowLogs] = useState(false);
  const [textScale, setTextScale] = useState(100);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [job.logs]);

  useEffect(() => {
    setTextScale(100);
  }, []);

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <DialogTitle className="flex items-center justify-between">
            <span>Blog Generation: {job.topic}</span>
            <div className="flex items-center space-x-2">
              <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                job.status === 'completed' ? 'bg-green-100 text-green-800' :
                job.status === 'failed' ? 'bg-red-100 text-red-800' :
                job.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {job.status.replace('_', ' ')}
              </span>
            </div>
          </DialogTitle>
        </DialogHeader>
        
        <div className="flex flex-col space-y-4 flex-1 min-h-0">
          {/* Progress Section */}
          <div className="space-y-2 flex-shrink-0">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Progress</span>
              <span className="text-sm text-gray-500">{Math.round(job.progress)}%</span>
            </div>
            <Progress value={job.progress} className="w-full" />
            <p className="text-sm text-gray-600 break-words whitespace-pre-wrap">
              {job.currentStep}
            </p>
          </div>

          {/* Error Display */}
          {job.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex-shrink-0">
              <h4 className="font-semibold text-red-800 mb-2">Error</h4>
              <p className="text-sm text-red-700">{job.error.user_message}</p>
              {job.error.suggestions && job.error.suggestions.length > 0 && (
                <div className="mt-2">
                  <p className="text-sm font-medium text-red-800">Suggestions:</p>
                  <ul className="text-sm text-red-700 list-disc list-inside">
                    {job.error.suggestions.map((suggestion, index) => (
                      <li key={index}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Tabs for Content and Logs */}
          <div className="flex space-x-4 border-b flex-shrink-0">
            <button
              className={`pb-2 px-1 border-b-2 font-medium text-sm ${
                !showLogs ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'
              }`}
              onClick={() => setShowLogs(false)}
            >
              Generated Content
            </button>
            <button
              className={`pb-2 px-1 border-b-2 font-medium text-sm ${
                showLogs ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500'
              }`}
              onClick={() => setShowLogs(true)}
            >
              Logs ({job.logs.length})
            </button>
          </div>

          {/* Content Display */}
          <div className="flex-1 min-h-0">
            {!showLogs ? (
              <BlogContentDisplay 
                content={job.blogContent} 
                status={job.status}
                textScale={textScale}
                onTextScaleChange={setTextScale}
              />
            ) : (
              <LogsDisplay logs={job.logs} logsEndRef={logsEndRef} />
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Sub-components for better organization
function BlogContentDisplay({ 
  content, 
  status, 
  textScale, 
  onTextScaleChange 
}: {
  content: string;
  status: string;
  textScale: number;
  onTextScaleChange: (scale: number) => void;
}) {
  return (
    <div className="h-full overflow-y-auto border border-gray-200 rounded-lg">
      {content ? (
        <div className="p-4">
          <div className="flex items-center justify-between mb-4 sticky top-0 bg-white z-10 pb-2 border-b">
            <h3 className="text-lg font-semibold">Generated Blog Content</h3>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500">Text Size:</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onTextScaleChange(Math.max(50, textScale - 10))}
              >
                -
              </Button>
              <span className="text-sm min-w-[3rem] text-center">{textScale}%</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onTextScaleChange(Math.min(200, textScale + 10))}
              >
                +
              </Button>
            </div>
          </div>
          <div 
            className="prose prose-sm max-w-none blog-content-container"
            style={{ fontSize: `${textScale}%` }}
          >
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ children }) => <h1 className="text-2xl font-bold mb-4 text-gray-900">{children}</h1>,
                h2: ({ children }) => <h2 className="text-xl font-semibold mb-3 text-gray-900">{children}</h2>,
                h3: ({ children }) => <h3 className="text-lg font-medium mb-2 text-gray-900">{children}</h3>,
                p: ({ children }) => <div className="mb-4 text-gray-700 leading-relaxed">{children}</div>,
                ul: ({ children }) => <ul className="list-disc list-inside mb-4 text-gray-700">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-inside mb-4 text-gray-700">{children}</ol>,
                li: ({ children }) => <li className="mb-1">{children}</li>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-blue-500 pl-4 italic text-gray-600 mb-4">
                    {children}
                  </blockquote>
                ),
                code: ({ children }) => (
                  <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono text-gray-800">
                    {children}
                  </code>
                ),
                pre: ({ children }) => (
                  <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto text-sm mb-4">
                    {children}
                  </pre>
                ),
                img: ({ src, alt, title }) => {
                  const imageSrc = typeof src === 'string' ? src : '/placeholder.png';
                  return (
                    <>
                      <Image 
                        src={imageSrc} 
                        alt={alt || 'Blog image'} 
                        title={title}
                        width={800}
                        height={400}
                        className="block max-w-full h-auto rounded-lg shadow-md mx-auto my-6"
                        style={{ maxHeight: '400px' }}
                      />
                      {title && (
                        <em className="block text-sm text-gray-500 text-center mt-2">{title}</em>
                      )}
                    </>
                  );
                },
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        </div>
      ) : (
        <div className="text-center text-gray-500 py-8">
          {status === 'completed' ? 'No content generated' : 'Content will appear here when generation is complete'}
        </div>
      )}
    </div>
  );
}

function LogsDisplay({ 
  logs, 
  logsEndRef 
}: {
  logs: Array<{
    task_id: string;
    log: string;
    timestamp: string;
  }>;
  logsEndRef: React.RefObject<HTMLDivElement | null>;
}) {
  return (
    <div className="h-full overflow-y-auto border border-gray-200 rounded-lg">
      <div className="space-y-2 p-4">
        {logs.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            No logs yet. Logs will appear here as the generation progresses.
          </div>
        ) : (
          <>
            {logs.map((log, index) => (
              <div key={index} className="text-sm bg-gray-50 p-3 rounded border-l-4 border-blue-500">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <pre className="whitespace-pre-wrap text-gray-700 font-mono text-xs">
                      {log.log}
                    </pre>
                  </div>
                  <span className="text-xs text-gray-500 ml-2 flex-shrink-0">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              </div>
            ))}
            <div ref={logsEndRef} />
          </>
        )}
      </div>
    </div>
  );
}
