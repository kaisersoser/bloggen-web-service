"use client"
import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { useAuth, useRoleCheck } from "@/hooks/useAuth";
import { useUserStats } from "@/hooks/useUserStats";
import { useInfiniteScroll } from "@/hooks/useInfiniteScroll";
import { BlogCard } from "@/components/blog/BlogCard";
import { DeleteConfirmationDialog } from "@/components/blog/DeleteConfirmationDialog";
import { UserProfile } from "@/components/auth/UserProfile";
import { signIn } from "next-auth/react";

interface BlogData {
  id: string
  userId: string
  topic: string
  instructions: string | null
  content: string | null
  status: string
  progress: number
  currentStep: string | null
  error: string | null
  createdAt: Date
  updatedAt: Date
  completedAt: Date | null
}

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

interface SSEUpdate {
  type: 'connected' | 'status_update' | 'stream_ended' | 'error';
  task_id: string;
  status?: string;
  current_step?: string;
  progress?: number;
  result?: string;
  error?: string;
  message?: string;
  timestamp?: string;
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
  const { isAuthenticated, isLoading } = useAuth();
  const { canGenerateBlog, isFree } = useRoleCheck();
  const { stats, loading: statsLoading, refetch: refetchStats } = useUserStats();
  
  const [topic, setTopic] = useState("");
  const [instructions, setInstructions] = useState("");
  const [jobs, setJobs] = useState<JobState[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [showJobDetails, setShowJobDetails] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [textScale, setTextScale] = useState(100);
  const [activeView, setActiveView] = useState<'form' | 'jobs' | 'details'>('form');
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [previousBlogs, setPreviousBlogs] = useState<BlogData[]>([]);
  const [blogsLoading, setBlogsLoading] = useState(false);
  
  // Delete confirmation dialog state
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [blogToDelete, setBlogToDelete] = useState<BlogData | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // Infinite scroll hook for previous blogs
  const { displayedBlogs, hasMore, isLoading: scrollLoading } = useInfiniteScroll({
    allBlogs: previousBlogs,
    itemsPerPage: 6
  });
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const completedTasksRef = useRef<Set<string>>(new Set());

  // Function to fetch user's previous blogs
  const fetchPreviousBlogs = async () => {
    if (!isAuthenticated) return;
    
    try {
      setBlogsLoading(true);
      const response = await fetch('/api/blogs');
      if (response.ok) {
        const data = await response.json();
        setPreviousBlogs(data.blogs || []);
      } else {
        console.error('Failed to fetch previous blogs:', response.statusText);
      }
    } catch (error) {
      console.error('Error fetching previous blogs:', error);
    } finally {
      setBlogsLoading(false);
    }
  };

  // Function to convert blog data to job state for modal display
  const convertBlogToJob = (blog: BlogData): JobState => {
    return {
      id: blog.id,
      topic: blog.topic,
      instructions: blog.instructions || '',
      status: blog.status.toLowerCase() as JobState['status'],
      progress: blog.progress,
      currentStep: blog.currentStep || 'Completed',
      logs: [], // Previous blogs don't have logs
      blogContent: blog.content || '',
      error: blog.error ? {
        error_type: 'generation_error',
        user_message: blog.error,
        technical_details: blog.error,
        is_recoverable: false,
        suggestions: [],
        timestamp: new Date().toISOString(),
        severity: 'error'
      } : null,
      createdAt: new Date(blog.createdAt).toISOString(),
      completedAt: blog.completedAt ? new Date(blog.completedAt).toISOString() : undefined
    };
  };

  // Utility function to create SSE connection for a task
  const connectToTaskStream = async (taskId: string): Promise<EventSource> => {
    try {
      // Get JWT token for SSE authentication
      const tokenResponse = await fetch('/api/auth/jwt-token', {
        method: 'GET',
        credentials: 'include'
      });
      
      if (!tokenResponse.ok) {
        throw new Error('Failed to get authentication token');
      }
      
      const { token } = await tokenResponse.json();
      
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'https://localhost:5000';
      const streamUrl = `${backendUrl}/stream/${taskId}?token=${encodeURIComponent(token)}`;
      
      console.log('🔌 Connecting to SSE stream:', streamUrl);
      
      const eventSource = new EventSource(streamUrl);
      
      eventSource.onopen = () => {
        console.log('✅ SSE connection established for task:', taskId);
      };
      
      eventSource.onmessage = (event) => {
        try {
          const data: SSEUpdate = JSON.parse(event.data);
          console.log('📡 SSE update received:', data);
          
          switch (data.type) {
            case 'connected':
              console.log('✅ Connected to task stream:', data.task_id);
              break;
              
            case 'status_update':
              console.log('📝 Status update:', data);
              updateJob(data.task_id, {
                status: data.status as JobState['status'],
                currentStep: data.current_step || 'Processing...',
                progress: Math.round((data.progress || 0) * 100)
              });
              
              // Add log entry for status updates
              const logEntry: LogUpdate = {
                task_id: data.task_id,
                log: `📊 ${data.current_step}`,
                timestamp: data.timestamp || new Date().toISOString()
              };
              
              setJobs(prevJobs => 
                prevJobs.map(job => 
                  job.id === data.task_id 
                    ? { ...job, logs: [...job.logs, logEntry] }
                    : job
                )
              );
              
              // Handle completion
              if (data.status === 'completed' && data.result) {
                handleTaskCompletion(data.task_id, data.result);
                // Close the SSE connection after completion
                eventSourceRef.current?.close();
              }
              
              // Handle errors  
              if (data.status === 'failed' && data.error) {
                handleTaskError(data.task_id, data.error);
                // Close the SSE connection after failure
                eventSourceRef.current?.close();
              }
              break;
              
            case 'stream_ended':
              console.log('🏁 Stream ended for task:', data.task_id);
              // Ensure connection is closed
              eventSourceRef.current?.close();
              break;
              
            case 'error':
              console.error('❌ Stream error:', data.message);
              break;
          }
        } catch (error) {
          console.error('Failed to parse SSE data:', error);
        }
      };
      
      eventSource.onerror = (error) => {
        console.error('❌ SSE connection error:', error);
        // Close connection on error to prevent endless reconnection attempts
        eventSource.close();
      };
      
      return eventSource;
      
    } catch (error) {
      console.error('Failed to create SSE connection:', error);
      throw error;
    }
  };

  // Handle task completion
  const handleTaskCompletion = async (taskId: string, content: string) => {
    // Prevent duplicate completion handling
    if (completedTasksRef.current.has(taskId)) {
      console.log('⚠️ Task already completed, skipping:', taskId);
      return;
    }
    
    console.log('✅ Task completed:', taskId);
    completedTasksRef.current.add(taskId);
    
    updateJob(taskId, {
      status: 'completed',
      currentStep: 'Blog generation complete!',
      progress: 100,
      blogContent: content,
      completedAt: new Date().toISOString()
    });
    
    // Notify backend of successful completion
    try {
      const response = await fetch('/api/blog-complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          blog_id: taskId,
          status: 'completed',
          content: content
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('Blog completion processed:', result);
        // Refetch user stats to update generation count
        refetchStats();
        // Refetch previous blogs to include the new completed blog
        fetchPreviousBlogs();
      }
    } catch (error) {
      console.error('Failed to update blog completion status:', error);
    }
  };

  // Handle task errors
  const handleTaskError = async (taskId: string, errorMessage: string) => {
    console.error('❌ Task failed:', taskId, errorMessage);
    
    const errorInfo: ErrorInfo = {
      error_type: 'generation_error',
      user_message: errorMessage,
      technical_details: errorMessage,
      is_recoverable: false,
      suggestions: ['Please try again with a different topic'],
      timestamp: new Date().toISOString(),
      severity: 'error'
    };
    
    updateJob(taskId, {
      status: 'failed',
      currentStep: 'Generation failed',
      progress: 0,
      error: errorInfo
    });
    
    // Notify backend of failure
    try {
      await fetch('/api/blog-complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          blog_id: taskId,
          status: 'failed',
          error: errorInfo
        })
      });
    } catch (error) {
      console.error('Failed to update blog completion status:', error);
    }
  };

  // Cleanup SSE connections on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Auto-scroll logs
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [jobs]);

  // Reset text scale when modal opens
  useEffect(() => {
    if (showJobDetails) {
      setTextScale(100);
    }
  }, [showJobDetails]);

  // Fetch previous blogs when user is authenticated
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      fetchPreviousBlogs();
    }
  }, [isAuthenticated, isLoading]);

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="max-w-6xl mx-auto p-4 space-y-4">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  // Show sign-in prompt if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto p-4 space-y-4">
        <div className="text-center py-12">
          <h1 className="text-3xl font-bold mb-4">AI Blog Generator</h1>
          <p className="text-gray-600 mb-8">Sign in to start generating amazing blogs with AI</p>
          <Button onClick={() => signIn()}>Sign In</Button>
        </div>
      </div>
    );
  }

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
    
    // Only start SSE stream if job is not completed or failed
    const job = jobs.find(j => j.id === jobId);
    if (job && job.status !== 'completed' && job.status !== 'failed') {
      // Check if we need to start SSE for in-progress job
      if (!eventSourceRef.current) {
        console.log('📡 Reconnecting to SSE stream for in-progress task:', jobId);
        connectToTaskStream(jobId)
          .then(eventSource => {
            eventSourceRef.current = eventSource;
          })
          .catch(error => {
            console.error('Failed to reconnect SSE stream:', error);
          });
      }
    } else {
      console.log('✋ Not starting SSE for completed/failed task:', jobId);
    }
  };

  // Helper function to close job details
  const closeJobDetails = () => {
    setShowJobDetails(false);
    setSelectedJobId(null);
    
    // Close any active SSE connection
    if (eventSourceRef.current) {
      console.log('🔌 Closing SSE connection');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  };

  // Helper function to delete completed jobs
  const deleteJob = (jobId: string) => {
    setJobs(prevJobs => prevJobs.filter(job => job.id !== jobId));
    if (selectedJobId === jobId) {
      closeJobDetails();
    }
  };

  // Function to handle delete blog request
  const handleDeleteBlog = (blogId: string) => {
    const blog = previousBlogs.find(b => b.id === blogId);
    if (blog) {
      setBlogToDelete(blog);
      setShowDeleteDialog(true);
    }
  };

  // Function to confirm and execute blog deletion
  const confirmDeleteBlog = async () => {
    if (!blogToDelete) return;

    try {
      setIsDeleting(true);
      
      const response = await fetch(`/api/blogs/delete?id=${blogToDelete.id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        // Remove the blog from the list
        setPreviousBlogs(prevBlogs => 
          prevBlogs.filter(blog => blog.id !== blogToDelete.id)
        );
        
        // Close dialog
        setShowDeleteDialog(false);
        setBlogToDelete(null);
        
        // Show success message (optional)
        console.log('Blog deleted successfully');
      } else {
        const errorData = await response.json();
        console.error('Failed to delete blog:', errorData.error);
        // You could show an error toast here
      }
    } catch (error) {
      console.error('Error deleting blog:', error);
      // You could show an error toast here
    } finally {
      setIsDeleting(false);
    }
  };

  // Function to cancel delete operation
  const cancelDeleteBlog = () => {
    setShowDeleteDialog(false);
    setBlogToDelete(null);
    setIsDeleting(false);
  };

  // Function to handle clicking on a previous blog card
  const openPreviousBlogDetails = (blog: BlogData) => {
    const jobState = convertBlogToJob(blog);
    // Add the blog as a temporary job to display in modal
    setJobs(prevJobs => {
      const existingIndex = prevJobs.findIndex(job => job.id === blog.id);
      if (existingIndex >= 0) {
        // Update existing job
        const newJobs = [...prevJobs];
        newJobs[existingIndex] = jobState;
        return newJobs;
      } else {
        // Add as new job
        return [...prevJobs, jobState];
      }
    });
    
    setSelectedJobId(blog.id);
    setActiveView('details');
    setShowJobDetails(true);
  };

  const handleGenerateBlog = async () => {
    if (!topic.trim()) {
      setGenerationError('Please enter a topic');
      return;
    }

    // Use fresh stats if available, fallback to session-based check
    const canGenerate = stats ? stats.remainingGenerations > 0 || stats.monthlyLimit === -1 : canGenerateBlog();
    if (!canGenerate) {
      setGenerationError('Monthly generation limit reached. Upgrade to Premium for unlimited access.');
      return;
    }

    try {
      setGenerationError(null);
      
      // Clear any previously completed tasks to allow new completions
      completedTasksRef.current.clear();
      
      const response = await fetch("/api/generate-blog", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          topic: topic.trim(),
          instructions: instructions.trim() || undefined
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || data.error || "Failed to start blog generation");
      }
      
      // Create new job and add to jobs list
      const newJob = createJob(data.task_id, topic.trim(), instructions.trim());
      setJobs(prevJobs => [...prevJobs, newJob]);
      
      // Set this job as selected and show progress
      setSelectedJobId(data.task_id);
      setActiveView('details');
      setShowJobDetails(true);
      
      // Start SSE stream for real-time updates
      console.log('📡 Starting SSE stream for task:', data.task_id);
      try {
        const eventSource = await connectToTaskStream(data.task_id);
        eventSourceRef.current = eventSource;
      } catch (sseError) {
        console.error('Failed to start SSE stream:', sseError);
        // Continue without SSE - user can still check status manually
      }
      
      // Clear form
      setTopic('');
      setInstructions('');
      
    } catch (error) {
      console.error("Error starting blog generation:", error);
      setGenerationError(error instanceof Error ? error.message : 'Failed to start blog generation. Please try again.');
    }
  };

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
            Jobs ({jobs.length + previousBlogs.length})
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-3">
          {/* New Blog Form */}
          {activeView === 'form' && (
            <Card>
              <CardHeader>
                <CardTitle>Generate New Blog</CardTitle>
                {isFree && stats && (
                  <p className="text-sm text-gray-600">
                    {stats.remainingGenerations} of {stats.monthlyLimit} free generations remaining this month
                  </p>
                )}
                {isFree && !stats && (
                  <p className="text-sm text-gray-600">
                    Loading generation limits...
                  </p>
                )}
              </CardHeader>
              <CardContent className="space-y-4">
                {generationError && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-sm text-red-700">{generationError}</p>
                  </div>
                )}
                
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
                  disabled={!topic.trim() || (!stats || (stats.remainingGenerations <= 0 && stats.monthlyLimit !== -1)) || statsLoading}
                  className="w-full"
                >
                  {!stats ? 'Loading...' : 
                   (stats.remainingGenerations > 0 || stats.monthlyLimit === -1) ? 'Generate Blog' : 'Monthly Limit Reached'}
                </Button>
                
                {isFree && stats && stats.remainingGenerations === 0 && (
                  <div className="text-center">
                    <p className="text-sm text-gray-600 mb-2">
                      Upgrade to Premium for unlimited blog generation
                    </p>
                    <Button variant="outline" size="sm">
                      Upgrade Now
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Previous Blogs Section - Show in form view */}
          {activeView === 'form' && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Previous Blogs</CardTitle>
              </CardHeader>
              <CardContent>
                {blogsLoading ? (
                  <div className="flex justify-center items-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                  </div>
                ) : previousBlogs.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No previous blogs yet. Generate your first blog above!
                  </div>
                ) : (
                  <div>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {displayedBlogs.map((blog) => (
                        <BlogCard
                          key={blog.id}
                          blog={blog}
                          onClick={openPreviousBlogDetails}
                          onDelete={handleDeleteBlog}
                        />
                      ))}
                    </div>
                    
                    {/* Infinite scroll sentinel */}
                    {hasMore && (
                      <div id="blog-scroll-sentinel" className="flex justify-center items-center py-8">
                        {scrollLoading ? (
                          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                        ) : (
                          <div className="text-sm text-gray-500">Scroll to load more blogs...</div>
                        )}
                      </div>
                    )}
                    
                    {!hasMore && displayedBlogs.length > 6 && (
                      <div className="text-center py-4">
                        <p className="text-sm text-gray-500">You&apos;ve reached the end of your blogs</p>
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Jobs Dashboard */}
          {activeView === 'jobs' && (
            <Card>
              <CardHeader>
                <CardTitle>Blog Generation Jobs & History</CardTitle>
              </CardHeader>
              <CardContent>
                {/* Active Jobs Section */}
                {jobs.length > 0 && (
                  <div className="mb-8">
                    <h3 className="text-lg font-semibold mb-4 text-gray-800">Active Jobs</h3>
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
                  </div>
                )}

                {/* Previous Blogs Section */}
                <div>
                  <h3 className="text-lg font-semibold mb-4 text-gray-800">Previous Blogs</h3>
                  {blogsLoading ? (
                    <div className="flex justify-center items-center py-8">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    </div>
                  ) : previousBlogs.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      No previous blogs yet. Create your first blog!
                    </div>
                  ) : (
                    <div>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {displayedBlogs.map((blog) => (
                          <BlogCard
                            key={blog.id}
                            blog={blog}
                            onClick={openPreviousBlogDetails}
                            onDelete={handleDeleteBlog}
                          />
                        ))}
                      </div>
                      
                      {/* Infinite scroll sentinel */}
                      {hasMore && (
                        <div id="blog-scroll-sentinel" className="flex justify-center items-center py-8">
                          {scrollLoading ? (
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                          ) : (
                            <div className="text-sm text-gray-500">Scroll to load more blogs...</div>
                          )}
                        </div>
                      )}
                      
                      {!hasMore && displayedBlogs.length > 6 && (
                        <div className="text-center py-4">
                          <p className="text-sm text-gray-500">You&apos;ve reached the end of your blogs</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-1">
          <UserProfile />
        </div>
      </div>

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

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmationDialog
        isOpen={showDeleteDialog}
        onClose={cancelDeleteBlog}
        onConfirm={confirmDeleteBlog}
        blogTopic={blogToDelete?.topic || ''}
        isDeleting={isDeleting}
      />
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
