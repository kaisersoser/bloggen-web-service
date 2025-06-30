"use client"
import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import ReactMarkdown from "react-markdown";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { io, Socket } from "socket.io-client";
import { Progress } from "@/components/ui/progress";

interface TaskStatus {
  task_id: string;
  status: 'queued' | 'in_progress' | 'completed' | 'failed';
  current_step?: string;
  result?: string;
  error?: string;
  created_at: string;
  completed_at?: string;
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

export default function BlogGenerator() {
  const [topic, setTopic] = useState("");
  const [instructions, setInstructions] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
  const [blogContent, setBlogContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState("");
  const [logs, setLogs] = useState<LogUpdate[]>([]);
  const [showLogs, setShowLogs] = useState(false);
  const [textScale, setTextScale] = useState(100); // Text scaling percentage
  
  const socketRef = useRef<Socket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Initialize socket connection
    socketRef.current = io("http://localhost:5000");
    
    // Socket event listeners
    socketRef.current.on('connected', (data: any) => {
      console.log('Connected to server:', data.message);
    });

    socketRef.current.on('status_update', (data: StatusUpdate) => {
      console.log('Status update:', data);
      setCurrentStep(data.message);
      if (data.step && data.total_steps) {
        setProgress((data.step / data.total_steps) * 100);
      }
    });

    socketRef.current.on('log_update', (data: LogUpdate) => {
      setLogs(prevLogs => [...prevLogs, data]);
    });

    socketRef.current.on('generation_complete', (data: any) => {
      console.log('Generation complete:', data);
      setBlogContent(data.content);
      setLoading(false);
      setProgress(100);
      setCurrentStep('Completed successfully!');
      setShowModal(true);
    });

    socketRef.current.on('generation_error', (data: any) => {
      console.error('Generation error:', data);
      setLoading(false);
      setCurrentStep(`Error: ${data.error}`);
    });

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, []);

  useEffect(() => {
    // Auto-scroll logs to bottom
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const handleGenerateBlog = async () => {
    if (!topic.trim()) {
      alert('Please enter a topic');
      return;
    }

    setLoading(true);
    setBlogContent("");
    setLogs([]);
    setProgress(0);
    setCurrentStep('Submitting request...');
    
    try {
      const response = await fetch("http://localhost:5000/generate-blog", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ topic }),
      });

      if (!response.ok) {
        throw new Error("Failed to start blog generation");
      }

      const data = await response.json();
      setTaskId(data.task_id);
      setCurrentStep('Blog generation started...');
      setShowStatusModal(true);
      
      // Join the task room for real-time updates
      if (socketRef.current) {
        socketRef.current.emit('join_task', { task_id: data.task_id });
      }
      
    } catch (error) {
      console.error("Error starting blog generation:", error);
      setLoading(false);
      setCurrentStep('Failed to start generation');
    }
  };

  const checkTaskStatus = async () => {
    if (!taskId) return;
    
    try {
      const response = await fetch(`http://localhost:5000/task-status/${taskId}`);
      if (response.ok) {
        const status: TaskStatus = await response.json();
        setTaskStatus(status);
      }
    } catch (error) {
      console.error("Error checking task status:", error);
    }
  };

  // Reset text scale when modal opens
  useEffect(() => {
    if (showModal) {
      setTextScale(100);
    }
  }, [showModal]);

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>AI Blog Generator</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">Blog Topic</label>
            <Input
              placeholder="Enter blog topic (e.g., 'The Future of AI in Healthcare')"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              disabled={loading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Writing Instructions (Optional)</label>
            <Textarea
              placeholder="Enter specific instructions for tone, style, target audience, etc."
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              disabled={loading}
              rows={3}
            />
          </div>
          <Button 
            onClick={handleGenerateBlog} 
            disabled={loading || !topic.trim()}
            className="w-full"
          >
            {loading ? "Generating Blog..." : "Generate Blog"}
          </Button>
        </CardContent>
      </Card>

      {blogContent && (
        <Card>
          <CardContent className="space-y-2 pt-6">
            <h2 className="text-lg font-semibold text-green-600">✅ Blog Ready!</h2>
            <p className="text-sm text-gray-600">Your blog post has been generated successfully.</p>
            <Button onClick={() => setShowModal(true)}>View Generated Blog</Button>
          </CardContent>
        </Card>
      )}

      {/* Status Modal */}
      <Dialog open={showStatusModal} onOpenChange={setShowStatusModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Blog Generation Progress</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-medium">Progress</span>
                <span className="text-sm text-gray-500">{Math.round(progress)}%</span>
              </div>
              <Progress value={progress} className="w-full" />
            </div>
            
            <div>
              <p className="text-sm font-medium mb-1">Current Step:</p>
              <p className="text-sm text-gray-600">{currentStep}</p>
            </div>

            <div className="flex space-x-2">
              <Button 
                variant="outline" 
                onClick={() => setShowLogs(!showLogs)}
                size="sm"
              >
                {showLogs ? 'Hide Logs' : 'Show Real-time Logs'}
              </Button>
              <Button 
                variant="outline" 
                onClick={checkTaskStatus}
                size="sm"
              >
                Refresh Status
              </Button>
            </div>

            {showLogs && (
              <div className="border rounded-lg p-4 bg-gray-50 max-h-60 overflow-y-auto">
                <h4 className="text-sm font-medium mb-2">Real-time Logs:</h4>
                <div className="space-y-1 text-xs font-mono">
                  {logs.map((log, index) => (
                    <div key={index} className="text-gray-700">
                      <span className="text-gray-500">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                      {" "}{log.log}
                    </div>
                  ))}
                  <div ref={logsEndRef} />
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Blog Content Modal */}
      <Dialog open={showModal} onOpenChange={setShowModal}>
        <DialogContent className="max-w-[90vw] w-full max-h-[90vh] p-0">
          <DialogHeader className="p-6 pb-2">
            <DialogTitle className="flex items-center justify-between">
              <span>Generated Blog Post</span>
              <div className="flex items-center space-x-2">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setTextScale(prev => Math.min(prev + 10, 150))}
                >
                  A+
                </Button>
                <span className="text-xs text-gray-500 min-w-12 text-center">
                  {textScale}%
                </span>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setTextScale(prev => Math.max(prev - 10, 70))}
                >
                  A-
                </Button>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setTextScale(100)}
                >
                  Reset
                </Button>
              </div>
            </DialogTitle>
          </DialogHeader>
          
          {/* A4-proportioned container with scrolling */}
          <div className="flex-1 overflow-hidden">
            <div 
              className="h-full overflow-y-auto overflow-x-auto bg-gray-100 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100"
              style={{ 
                minHeight: '70vh',
                maxHeight: '75vh'
              }}
            >
              {/* A4 paper container */}
              <div 
                className="blog-content mx-auto bg-white shadow-xl border border-gray-300 my-4"
                style={{
                  width: 'min(210mm, calc(100vw - 2rem))',
                  minHeight: '297mm',
                  maxWidth: '100%',
                  padding: 'min(20mm, 1.5rem)',
                  fontSize: `${textScale/100}em`,
                  lineHeight: '1.6',
                  fontFamily: 'Georgia, "Times New Roman", serif',
                  transition: 'font-size 0.2s ease-in-out'
                }}
              >
                <div className="prose prose-lg max-w-none">
                  <ReactMarkdown 
                    components={{
                      h1: ({children}) => <h1 className="text-3xl font-bold mb-6 text-gray-900 border-b-2 border-gray-200 pb-3">{children}</h1>,
                      h2: ({children}) => <h2 className="text-2xl font-semibold mt-8 mb-4 text-gray-800">{children}</h2>,
                      h3: ({children}) => <h3 className="text-xl font-semibold mt-6 mb-3 text-gray-800">{children}</h3>,
                      p: ({children}) => <p className="mb-4 text-gray-700 text-justify leading-relaxed">{children}</p>,
                      ul: ({children}) => <ul className="mb-4 pl-6 space-y-2">{children}</ul>,
                      ol: ({children}) => <ol className="mb-4 pl-6 space-y-2">{children}</ol>,
                      li: ({children}) => <li className="text-gray-700">{children}</li>,
                      blockquote: ({children}) => (
                        <blockquote className="border-l-4 border-blue-500 pl-4 py-2 my-4 bg-blue-50 italic text-gray-700">
                          {children}
                        </blockquote>
                      ),
                      code: ({children}) => (
                        <code className="bg-gray-100 px-2 py-1 rounded text-sm font-mono text-gray-800">
                          {children}
                        </code>
                      ),
                      pre: ({children}) => (
                        <pre className="bg-gray-100 p-4 rounded-lg overflow-x-auto mb-4 text-sm">
                          {children}
                        </pre>
                      )
                    }}
                  >
                    {blogContent}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          </div>
          
          {/* Footer with additional controls */}
          <div className="p-4 border-t bg-gray-50 flex justify-between items-center">
            <div className="text-sm text-gray-600 flex items-center space-x-4">
              <span>📄 A4 Format</span>
              <span>🔍 Scale: {textScale}%</span>
              <span>📱 Scroll to read</span>
            </div>
            <div className="flex space-x-2">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => {
                  navigator.clipboard.writeText(blogContent);
                  // You could add a toast notification here
                }}
              >
                📋 Copy
              </Button>
              <Button 
                variant="outline"
                size="sm"
                onClick={() => {
                  const printContent = document.querySelector('.blog-content')?.innerHTML;
                  if (printContent) {
                    const printWindow = window.open('', '_blank');
                    if (printWindow) {
                      printWindow.document.write(`
                        <html>
                          <head>
                            <title>Blog Post</title>
                            <style>
                              body { 
                                font-family: Georgia, "Times New Roman", serif; 
                                line-height: 1.6; 
                                max-width: 210mm; 
                                margin: 0 auto; 
                                padding: 20mm;
                                font-size: 12pt;
                              }
                              h1 { border-bottom: 2px solid #ccc; padding-bottom: 12px; margin-bottom: 24px; }
                              h2 { margin-top: 32px; margin-bottom: 16px; }
                              h3 { margin-top: 24px; margin-bottom: 12px; }
                              p { text-align: justify; margin-bottom: 16px; }
                              ul, ol { margin-bottom: 16px; padding-left: 24px; }
                              li { margin-bottom: 8px; }
                              blockquote { 
                                border-left: 4px solid #3b82f6; 
                                padding-left: 16px; 
                                margin: 16px 0; 
                                background-color: #f8fafc; 
                                padding: 12px 16px; 
                              }
                              @media print {
                                body { margin: 0; padding: 15mm; }
                                h1 { page-break-after: avoid; }
                                h2, h3 { page-break-after: avoid; }
                              }
                            </style>
                          </head>
                          <body>${printContent}</body>
                        </html>
                      `);
                      printWindow.document.close();
                      printWindow.print();
                    }
                  }
                }}
              >
                🖨️ Print/PDF
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
