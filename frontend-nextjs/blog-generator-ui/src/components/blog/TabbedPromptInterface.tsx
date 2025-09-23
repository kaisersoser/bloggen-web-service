"use client"
import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { StreamingConsole } from "./StreamingConsole";
import { useConsoleMessages } from "@/hooks/useConsoleMessages";
import { useStreamingContent } from "@/hooks/useStreamingContent";
import { 
  Send, 
  Sparkles, 
  Loader2, 
  Zap, 
  Brain,
  Lightbulb,
  Target,
  Clock,
  Terminal,
  FileText,
  Search
} from "lucide-react";

interface TabbedPromptInterfaceProps {
  onSubmit: (prompt: string) => void;
  isGenerating?: boolean;
  disabled?: boolean;
  remainingGenerations?: number;
  userRole?: 'FREE' | 'PREMIUM' | 'ADMIN';
  className?: string;
  taskLogs?: Record<string, Array<{
    timestamp: string;
    step: string;
    message: string;
    progress: number;
  }>>;
  currentJobId?: string | null;
  clearTaskLogs?: () => void;
}

export const TabbedPromptInterface = ({
  onSubmit,
  isGenerating = false,
  disabled = false,
  remainingGenerations = 0,
  userRole = 'FREE',
  className = '',
  taskLogs = {},
  currentJobId = null,
  clearTaskLogs
}: TabbedPromptInterfaceProps) => {
  const [prompt, setPrompt] = useState<string>('');
  const [activeTab, setActiveTab] = useState<string>('instructions');
  const [isFocused, setIsFocused] = useState<boolean>(false);
  
  // Console streaming functionality 
  const { 
    messages, 
    addMessage, 
    clearMessages,
    formatTimestamp,
    getMessageIcon,
    getMessageColorClass,
    messagesEndRef,
    consoleContainerRef
  } = useConsoleMessages();

  // Draft content streaming functionality
  const {
    streamingContent,
    handleContentStreamMessage,
    resetStreamingContent,
    getStreamingStats
  } = useStreamingContent();

  // State for draft content modal
  const [isDraftModalOpen, setIsDraftModalOpen] = useState(false);

  // Auto-switch to console tab when generation starts
  React.useEffect(() => {
    if (isGenerating && activeTab === 'instructions') {
      setActiveTab('console');
    }
  }, [isGenerating, activeTab]);

  // Track the last processed log index to avoid duplicates
  const lastProcessedIndex = React.useRef<Record<string, number>>({});
  const processingQueue = React.useRef<Array<{ jobId: string; log: any; index: number }>>([]);
  const isProcessingQueue = React.useRef<boolean>(false);
  const isBlogCompleted = React.useRef<boolean>(false);

  // Detect blog completion based on isGenerating prop and completion messages
  React.useEffect(() => {
    const wasCompleted = isBlogCompleted.current;
    const isNowCompleted = !isGenerating && currentJobId; // Blog completed when generation stops
    
    // Also check for completion messages in task logs
    if (currentJobId && taskLogs[currentJobId]) {
      const logs = taskLogs[currentJobId];
      const hasCompletionMessage = logs.some(log => 
        log.message?.toLowerCase().includes('blog generation complete') ||
        log.message?.toLowerCase().includes('finalization complete') ||
        log.message?.toLowerCase().includes('content cleaning completed') ||
        log.step?.toLowerCase().includes('complete')
      );
      
      if (hasCompletionMessage && !wasCompleted) {
        console.log('🎯 Blog completion detected via completion message! Flushing remaining console messages...');
        isBlogCompleted.current = true;
        
        // Flush all remaining messages immediately
        if (processingQueue.current.length > 0) {
          console.log(`⚡ Fast-flushing ${processingQueue.current.length} remaining messages`);
          
          // Process all remaining messages without delays
          while (processingQueue.current.length > 0) {
            const { jobId, log, index } = processingQueue.current.shift()!;
            console.log(`➕ Fast-adding message ${index + 1}:`, log.message);
            
            addMessage(
              log.step || 'info',
              log.message,
              { progress: log.progress, timestamp: log.timestamp },
              'info'
            );
          }
          
          isProcessingQueue.current = false;
        }
      }
    }
    
    if (!wasCompleted && isNowCompleted) {
      console.log('🎯 Blog completion detected via isGenerating! Flushing remaining console messages...');
      isBlogCompleted.current = true;
      
      // Flush all remaining messages immediately
      if (processingQueue.current.length > 0) {
        console.log(`⚡ Fast-flushing ${processingQueue.current.length} remaining messages`);
        
        // Process all remaining messages without delays
        while (processingQueue.current.length > 0) {
          const { jobId, log, index } = processingQueue.current.shift()!;
          console.log(`➕ Fast-adding message ${index + 1}:`, log.message);
          
          addMessage(
            log.step || 'info',
            log.message,
            { progress: log.progress, timestamp: log.timestamp },
            'info'
          );
        }
        
        isProcessingQueue.current = false;
      }
    }
    
    // Reset completion flag for new jobs
    if (isGenerating && wasCompleted) {
      isBlogCompleted.current = false;
    }
  }, [isGenerating, currentJobId, addMessage, taskLogs]);

  // Sequential message processor with typewriter effect
  const processMessageQueue = React.useCallback(async () => {
    if (isProcessingQueue.current || processingQueue.current.length === 0) {
      return;
    }

    isProcessingQueue.current = true;

    while (processingQueue.current.length > 0) {
      // Check if blog is completed - if so, stop typewriter effect and let flush handle it
      if (isBlogCompleted.current) {
        console.log('🛑 Blog completed during typewriter processing, stopping to allow fast flush');
        isProcessingQueue.current = false;
        return;
      }

      const { jobId, log, index } = processingQueue.current.shift()!;
      
      console.log(`➕ Adding message ${index + 1} with typewriter effect:`, log.message);
      
      // Add the message
      addMessage(
        log.step || 'info',
        log.message,
        { progress: log.progress, timestamp: log.timestamp },
        'info'
      );

      // Calculate typewriter delay based on message length
      const messageLength = log.message?.length || 0;
      const typewriterDelay = Math.max(800, Math.min(3000, (messageLength / 30) * 1000 + 600));
      
      console.log(`⏰ Typewriter delay: ${typewriterDelay}ms for message length: ${messageLength}`);
      
      // Wait for typewriter effect (only if there are more messages and blog isn't completed)
      if (processingQueue.current.length > 0 && !isBlogCompleted.current) {
        await new Promise(resolve => setTimeout(resolve, typewriterDelay));
      }
    }

    isProcessingQueue.current = false;
  }, [addMessage]);

  // Convert taskLogs to console messages with sequential typewriter streaming
  React.useEffect(() => {
    if (currentJobId && taskLogs[currentJobId]) {
      const logs = taskLogs[currentJobId];
      const lastIndex = lastProcessedIndex.current[currentJobId] || 0;
      
      console.log('📊 TaskLogs processing:', {
        currentJobId,
        logsCount: logs.length,
        lastProcessedIndex: lastIndex,
        queueLength: processingQueue.current.length,
        blogCompleted: isBlogCompleted.current
      });
      
      // Only process new messages that haven't been processed yet
      if (logs.length > lastIndex) {
        const newLogs = logs.slice(lastIndex);
        
        console.log('✅ Queueing new logs for typewriter processing:', {
          newLogsCount: newLogs.length,
          startingFromIndex: lastIndex
        });
        
        // Add new messages to the processing queue
        newLogs.forEach((log, index) => {
          processingQueue.current.push({
            jobId: currentJobId,
            log,
            index: lastIndex + index
          });
        });
        
        // Update the last processed index
        lastProcessedIndex.current[currentJobId] = logs.length;
        
        // If blog is already completed, flush immediately, otherwise start typewriter processing
        if (isBlogCompleted.current) {
          console.log('⚡ Blog already completed, processing new messages immediately');
          
          // Process the new messages immediately without delays
          const newQueuedMessages = processingQueue.current.splice(-newLogs.length);
          newQueuedMessages.forEach(({ jobId, log, index }) => {
            console.log(`➕ Immediate-adding message ${index + 1}:`, log.message);
            addMessage(
              log.step || 'info',
              log.message,
              { progress: log.progress, timestamp: log.timestamp },
              'info'
            );
          });
        } else {
          // Start processing the queue with typewriter effect
          processMessageQueue();
        }
      }
    }
  }, [taskLogs, currentJobId, processMessageQueue, addMessage]);

  // Clean up processed index when job changes
  React.useEffect(() => {
    if (currentJobId && !lastProcessedIndex.current[currentJobId]) {
      lastProcessedIndex.current[currentJobId] = 0;
      // Clear queue and completion status for new job
      processingQueue.current = [];
      isProcessingQueue.current = false;
      isBlogCompleted.current = false;
    }
  }, [currentJobId]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim() && !isGenerating && !disabled) {
      // Clear console messages before starting new generation
      clearMessages();
      
      // Also clear taskLogs if the callback is provided
      if (clearTaskLogs) {
        clearTaskLogs();
        console.log('🧹 TaskLogs cleared for new blog generation');
      }
      
      console.log('🧹 Console cleared for new blog generation request');
      
      onSubmit(prompt.trim());
      setPrompt('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Check generation limits
  const isAtLimit = remainingGenerations !== undefined && remainingGenerations <= 0 && userRole !== 'ADMIN';

  return (
    <div className={`w-full max-w-4xl mx-auto ${className}`}>
      {/* Header Section */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 mb-4">
          <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            AI Blog Generator
          </h1>
        </div>
        
        <p className="text-gray-600 dark:text-gray-400 text-lg mb-4">
          Transform your ideas into engaging, well-researched blog posts with AI-powered content generation
        </p>

        <div className="flex items-center justify-center gap-6 text-sm">
          <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
            <Brain className="w-4 h-4" />
            <span>AI-powered research</span>
          </div>
          <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
            <Zap className="w-4 h-4" />
            <span>Real-time generation</span>
          </div>
          <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
            <Lightbulb className="w-4 h-4" />
            <span>Creative content</span>
          </div>
          {remainingGenerations !== undefined && userRole !== 'ADMIN' && (
            <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
              <Target className="w-4 h-4" />
              <span>
                {remainingGenerations} generations remaining
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Tabbed Interface */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                  <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger 
              value="instructions" 
              className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:text-gray-900"
            >
              <FileText className="h-4 w-4" />
              Instructions
            </TabsTrigger>
            <TabsTrigger 
              value="console" 
              className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:text-gray-900"
            >
              <Terminal className="h-4 w-4" />
              Console
              {messages.length > 0 && (
                <Badge variant="secondary" className="ml-1 text-xs bg-blue-100 text-blue-800">
                  {messages.length}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

        {/* Draft Content Preview Button - Only show during generation */}
        {(isGenerating || streamingContent.content_preview) && (
          <div className="flex justify-end mb-4">
            <Dialog open={isDraftModalOpen} onOpenChange={setIsDraftModalOpen}>
              <DialogTrigger asChild>
                <Button
                  variant="outline" 
                  size="sm"
                  className="flex items-center gap-2 hover:bg-blue-50 hover:border-blue-300"
                >
                  <Search className="h-4 w-4" />
                  Draft Preview
                  {streamingContent.content_paragraphs.length > 0 && (
                    <Badge variant="secondary" className="ml-1 text-xs bg-green-100 text-green-800">
                      {streamingContent.content_paragraphs.length}
                    </Badge>
                  )}
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2">
                    <Search className="h-5 w-5" />
                    Draft Blog Content Preview
                    <Badge variant="outline" className="text-xs">
                      {streamingContent.current_phase || 'Generating...'}
                    </Badge>
                  </DialogTitle>
                </DialogHeader>
                <div className="overflow-y-auto max-h-[60vh] space-y-6">
                  {/* Research Findings */}
                  {streamingContent.research_findings.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                        <Brain className="h-5 w-5 text-blue-600" />
                        Research Findings ({streamingContent.research_findings.length})
                      </h3>
                      <div className="space-y-2">
                        {streamingContent.research_findings.map((finding, index) => (
                          <div key={index} className="p-3 bg-blue-50 rounded-lg border-l-4 border-blue-400">
                            <p className="text-sm text-gray-700">{finding}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Content Paragraphs */}
                  {streamingContent.content_paragraphs.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                        <FileText className="h-5 w-5 text-green-600" />
                        Draft Content ({streamingContent.content_paragraphs.length} paragraphs)
                      </h3>
                      <div className="space-y-4">
                        {streamingContent.content_paragraphs.map((paragraph, index) => (
                          <div key={index} className="p-4 bg-green-50 rounded-lg">
                            <p className="text-gray-800 leading-relaxed">{paragraph}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Content Preview */}
                  {streamingContent.content_preview && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                        <FileText className="h-5 w-5 text-purple-600" />
                        Live Preview
                      </h3>
                      <div className="p-4 bg-purple-50 rounded-lg">
                        <div className="prose prose-sm max-w-none">
                          <pre className="whitespace-pre-wrap text-gray-800 font-sans">
                            {streamingContent.content_preview}
                          </pre>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Fact Corrections */}
                  {streamingContent.fact_corrections.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                        <Target className="h-5 w-5 text-orange-600" />
                        Fact Corrections ({streamingContent.fact_corrections.length})
                      </h3>
                      <div className="space-y-2">
                        {streamingContent.fact_corrections.map((correction, index) => (
                          <div key={index} className="p-3 bg-orange-50 rounded-lg border-l-4 border-orange-400">
                            <p className="text-sm text-gray-700">{correction}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* No content yet */}
                  {!streamingContent.content_preview && 
                   streamingContent.research_findings.length === 0 && 
                   streamingContent.content_paragraphs.length === 0 && (
                    <div className="text-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
                      <p className="text-gray-500">Waiting for content generation to begin...</p>
                    </div>
                  )}
                </div>
              </DialogContent>
            </Dialog>
          </div>
        )}

        {/* Instructions Tab - Current Prompt Interface */}
        <TabsContent value="instructions" className="space-y-4">
          <Card className={`p-6 transition-all duration-300 ${
            isFocused ? 'ring-2 ring-blue-500 shadow-lg' : 'shadow-md'
          } ${isGenerating ? 'ring-2 ring-blue-400 animate-pulse' : ''}`}>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Main Input */}
              <div className="relative">
                <Textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={handleKeyDown}
                  onFocus={() => setIsFocused(true)}
                  onBlur={() => setIsFocused(false)}
                  placeholder="Describe the blog topic you'd like to generate... (e.g., 'Latest trends in sustainable technology', 'How to build a productive morning routine', 'The future of remote work')"
                  className="min-h-[120px] text-base resize-none pr-16 leading-relaxed"
                  disabled={disabled || isGenerating || isAtLimit}
                />
                
                {/* Character count and send button overlay */}
                <div className="absolute bottom-3 right-3 flex items-end gap-2">
                  <span className="text-xs text-gray-400">
                    {prompt.length}/500
                  </span>
                  <Button
                    type="submit"
                    size="sm"
                    disabled={!prompt.trim() || isGenerating || disabled || isAtLimit}
                    className="h-8 w-8 p-0 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                  >
                    {isGenerating ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </Button>
                </div>
              </div>

              {/* Suggestion Pills */}
              <div className="flex flex-wrap gap-2">
                <span className="text-sm text-gray-500 dark:text-gray-400 mr-2">Try:</span>
                {[
                  "AI and machine learning trends",
                  "Sustainable business practices", 
                  "Remote work productivity tips",
                  "Digital marketing strategies"
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => setPrompt(suggestion)}
                    disabled={isGenerating || disabled || isAtLimit}
                    className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>

              {/* Status Messages */}
              {isAtLimit && (
                <div className="p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
                  <div className="flex items-center gap-2 text-orange-700 dark:text-orange-300">
                    <Clock className="w-4 h-4" />
                    <span className="text-sm font-medium">
                      You&apos;ve reached your monthly generation limit. 
                      {userRole === 'FREE' && ' Upgrade to Premium for more generations!'}
                    </span>
                  </div>
                </div>
              )}

              {isGenerating && (
                <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
                  <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-sm font-medium">
                      AI agents are collaborating to create your blog... Check the Console tab for real-time updates!
                    </span>
                  </div>
                </div>
              )}

              {/* Keyboard shortcut hint */}
              <div className="text-xs text-gray-400 text-center">
                <kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs">Cmd+Enter</kbd> to submit
              </div>
            </form>
          </Card>
        </TabsContent>

        {/* Console Tab - Streaming Notifications */}
        <TabsContent value="console" className="space-y-4">
          <Card className="p-6">
            {/* StreamingConsole Component - handles its own header */}
            <StreamingConsole 
              messages={messages}
              isGenerating={isGenerating}
              onClearMessages={clearMessages}
              formatTimestamp={formatTimestamp}
              getMessageIcon={getMessageIcon}
              getMessageColorClass={getMessageColorClass}
              messagesEndRef={messagesEndRef as React.RefObject<HTMLDivElement>}
              consoleContainerRef={consoleContainerRef as React.RefObject<HTMLDivElement>}
            />
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}