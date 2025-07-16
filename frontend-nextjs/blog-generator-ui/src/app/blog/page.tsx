"use client"
import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { io, Socket } from "socket.io-client";
import { Progress } from "@/components/ui/progress";
import { ErrorDisplay } from "@/components/ErrorDisplay";

interface JobState {
  id: string;
  topic: string;
  instructions: string;
  status: 'queued' | 'in_progress' | 'completed' | 'failed';
  progress: number;
  currentStep: string;
  logs: LogUpdate[];
  blogContent: string;
  error: ErrorInfo | null;
  createdAt: string;
  completedAt?: string;
}

interface StatusUpdate {
  task_id: string;
  status: string;
  message: string;
  step?: number;
  total_steps?: number;
}

interface LogUpdate {
  task_id: string;
  log: string;
  timestamp: string;
}

interface ErrorInfo {
  error_type: string;
  user_message: string;
  technical_details: string;
  is_recoverable: boolean;
  suggestions: string[];
  timestamp: string;
  severity: string;
}

export default function BlogGenerator() {
  const [topic, setTopic] = useState("");
  const [instructions, setInstructions] = useState("");
  const [jobs, setJobs] = useState<JobState[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [showJobDetails, setShowJobDetails] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [textScale, setTextScale] = useState(100);
  const [activeView, setActiveView] = useState<'form' | 'jobs' | 'details'>('form');
  
  const socketRef = useRef<Socket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Helper function to get selected job
  const getSelectedJob = () => {
    return jobs.find(job => job.id === selectedJobId);
  };
  
  // Helper function to update a specific job
  const updateJob = (jobId: string, updates: Partial<JobState>) => {
    setJobs(prevJobs => 
      prevJobs.map(job => 
        job.id === jobId ? { ...job, ...updates } : job
      )
    );
  };

  // Helper function to create a new job
  const createJob = (jobId: string, topic: string, instructions: string): JobState => {
    return {
      id: jobId,
      topic,
      instructions,
      status: 'queued',
      progress: 0,
      currentStep: 'Starting...',
      logs: [],
      blogContent: '',
      error: null,
      createdAt: new Date().toISOString()
    };
  };

  // Helper function to open job details
  const openJobDetails = (jobId: string) => {
    setSelectedJobId(jobId);
    setActiveView('details');
    setShowJobDetails(true);
  };

  // Helper function to close job details
  const closeJobDetails = () => {
    setShowJobDetails(false);
    setSelectedJobId(null);
  };

  // Helper function to delete completed jobs
  const deleteJob = (jobId: string) => {
    setJobs(prevJobs => prevJobs.filter(job => job.id !== jobId));
    if (selectedJobId === jobId) {
      closeJobDetails();
    }
  };

  useEffect(() => {
    socketRef.current = io("http://localhost:5000", {
      transports: ['websocket', 'polling'],
      timeout: 20000,
      forceNew: true,
      rememberUpgrade: false,
      upgrade: true
    });
    
    // Socket event listeners
    socketRef.current.on('connect', () => {
      // WebSocket connected successfully
    });
    
    socketRef.current.on('disconnect', () => {
      // WebSocket disconnected
    });

    socketRef.current.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
    });

    socketRef.current.on('connected', (data: { message: string }) => {
      // Connected to server
    });

    socketRef.current.on('joined_task', (data: { task_id: string; message: string }) => {
      // Joined task room
    });
    
    socketRef.current.on('status_update', (data: StatusUpdate) => {
      updateJob(data.task_id, {
        status: data.status as JobState['status'],
        currentStep: data.message,
        // Adjust progress calculation: step represents "starting step X", so progress should be (step-1)/total
        progress: data.step && data.total_steps ? ((data.step - 1) / data.total_steps) * 100 : 0
      });
    });

    socketRef.current.on('log_update', (data: LogUpdate) => {
      setJobs(prevJobs => 
        prevJobs.map(job => 
          job.id === data.task_id 
            ? { ...job, logs: [...job.logs, data] }
            : job
        )
      );
    });

    socketRef.current.on('generation_complete', (data: { task_id: string; status: string; message: string; content: string }) => {
      updateJob(data.task_id, {
        blogContent: data.content,
        status: 'completed',
        progress: 100,
        currentStep: 'Completed successfully!',
        completedAt: new Date().toISOString()
      });
    });

    socketRef.current.on('generation_error', (data: { task_id: string; status: string; error_info: ErrorInfo }) => {
      console.error('Generation error:', data.error_info);
      updateJob(data.task_id, {
        status: 'failed',
        error: data.error_info,
        currentStep: "Blog generation stopped due to an error. Please see details below."
      });
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  // Auto-scroll logs to bottom
  useEffect(() => {
    if (logsEndRef.current && selectedJobId) {
      const selectedJob = getSelectedJob();
      if (selectedJob && selectedJob.logs.length > 0) {
        logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    }
  }, [selectedJobId, jobs]);

  const handleGenerateBlog = async () => {
    if (!topic.trim()) {
      alert('Please enter a topic');
      return;
    }

    try {
      const response = await fetch("http://localhost:5000/generate-blog", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          topic: topic.trim(),
          instructions: instructions.trim() || undefined
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to start blog generation");
      }

      const data = await response.json();
      
      // Create new job and add to jobs list
      const newJob = createJob(data.task_id, topic.trim(), instructions.trim());
      setJobs(prevJobs => [...prevJobs, newJob]);
      
      // Set this job as selected and show progress
      setSelectedJobId(data.task_id);
      setActiveView('details');
      setShowJobDetails(true);
      
      // Join the task room for real-time updates
      if (socketRef.current) {
        socketRef.current.emit('join_task', { task_id: data.task_id });
      }
      
      // Clear form
      setTopic('');
      setInstructions('');
      
    } catch (error) {
      console.error("Error starting blog generation:", error);
      alert('Failed to start blog generation. Please try again.');
    }
  };

  // Reset text scale when modal opens
  useEffect(() => {
    if (showJobDetails) {
      setTextScale(100);
    }
  }, [showJobDetails]);

  return (
    <div className="max-w-6xl mx-auto p-4 space-y-4">
      {/* Header Navigation */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">AI Blog Generator</h1>
        <div className="flex space-x-2">
          <Button
            variant={activeView === 'form' ? 'default' : 'outline'}
            onClick={() => setActiveView('form')}
          >
            New Blog
          </Button>
          <Button
            variant={activeView === 'jobs' ? 'default' : 'outline'}
            onClick={() => setActiveView('jobs')}
          >
            Jobs ({jobs.length})
          </Button>
        </div>
      </div>

      {/* New Blog Form */}
      {activeView === 'form' && (
        <Card>
          <CardHeader>
            <CardTitle>Generate New Blog</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Blog Topic</label>
              <Input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="Enter your blog topic..."
                className="w-full"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Additional Instructions (Optional)</label>
              <Textarea
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Any specific requirements or style preferences..."
                className="min-h-[100px]"
              />
            </div>
            
            <Button
              onClick={handleGenerateBlog}
              disabled={!topic.trim()}
              className="w-full"
            >
              Generate Blog
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Jobs Dashboard */}
      {activeView === 'jobs' && (
        <Card>
          <CardHeader>
            <CardTitle>Blog Generation Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            {jobs.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No blog generation jobs yet. Create your first blog!
              </div>
            ) : (
              <div className="space-y-4">
                {jobs.map((job) => (
                  <div
                    key={job.id}
                    className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer"
                    onClick={() => openJobDetails(job.id)}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg">{job.topic}</h3>
                        <p className="text-sm text-gray-600 mt-1">{job.currentStep}</p>
                        <div className="flex items-center space-x-4 mt-2">
                          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                            job.status === 'completed' ? 'bg-green-100 text-green-800' :
                            job.status === 'failed' ? 'bg-red-100 text-red-800' :
                            job.status === 'in_progress' ? 'bg-blue-100 text-blue-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {job.status.replace('_', ' ')}
                          </span>
                          <span className="text-xs text-gray-500">
                            {new Date(job.createdAt).toLocaleString()}
                          </span>
                        </div>
                        {job.status === 'in_progress' && (
                          <div className="mt-2">
                            <Progress value={job.progress} className="w-full" />
                          </div>
                        )}
                      </div>
                      <div className="flex items-center space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            openJobDetails(job.id);
                          }}
                        >
                          View Details
                        </Button>
                        {job.status === 'completed' || job.status === 'failed' ? (
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteJob(job.id);
                            }}
                          >
                            Delete
                          </Button>
                        ) : null}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Job Details Modal */}
      {showJobDetails && selectedJobId && (
        <JobDetailsModal
          job={getSelectedJob()!}
          onClose={closeJobDetails}
          showLogs={showLogs}
          setShowLogs={setShowLogs}
          textScale={textScale}
          setTextScale={setTextScale}
          logsEndRef={logsEndRef}
        />
      )}
    </div>
  );
}

// Job Details Modal Component
function JobDetailsModal({
  job,
  onClose,
  showLogs,
  setShowLogs,
  textScale,
  setTextScale,
  logsEndRef
}: {
  job: JobState;
  onClose: () => void;
  showLogs: boolean;
  setShowLogs: (show: boolean) => void;
  textScale: number;
  setTextScale: (scale: number) => void;
  logsEndRef: React.RefObject<HTMLDivElement | null>;
}) {
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

          {/* Content Display - This will now take remaining space */}
          <div className="flex-1 min-h-0">
            {!showLogs ? (
              <div className="h-full overflow-y-auto border border-gray-200 rounded-lg">
                {job.blogContent ? (
                  <div className="p-4">
                    <div className="flex items-center justify-between mb-4 sticky top-0 bg-white z-10 pb-2 border-b">
                      <h3 className="text-lg font-semibold">Generated Blog Content</h3>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-gray-500">Text Size:</span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setTextScale(Math.max(50, textScale - 10))}
                        >
                          -
                        </Button>
                        <span className="text-sm min-w-[3rem] text-center">{textScale}%</span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setTextScale(Math.min(200, textScale + 10))}
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
                            return (
                              <>
                                <img 
                                  src={src} 
                                  alt={alt || 'Blog image'} 
                                  title={title}
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
                        {job.blogContent}
                      </ReactMarkdown>
                    </div>
                  </div>
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    {job.status === 'completed' ? 'No content generated' : 'Content will appear here when generation is complete'}
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full overflow-y-auto border border-gray-200 rounded-lg">
                <div className="space-y-2 p-4">
                  {job.logs.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                      No logs yet. Logs will appear here as the generation progresses.
                    </div>
                  ) : (
                    <>
                      {job.logs.map((log, index) => (
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
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
