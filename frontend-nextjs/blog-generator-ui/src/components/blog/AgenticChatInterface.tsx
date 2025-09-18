"use client"

import React, { useState, useRef, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Send, Bot, User, Loader2, FileText, Settings, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

interface LogEntry {
  timestamp: string;
  step: string;
  message: string;
  progress: number;
}

interface JobState {
  id: string;
  status: 'pending' | 'queued' | 'in_progress' | 'completed' | 'failed';
  currentStep: string;
  progress: number;
  createdAt: Date;
}

interface AgenticChatInterfaceProps {
  onGenerateBlog: (topic: string) => void;
  currentJob: JobState | null;
  isGenerating: boolean;
  logs: LogEntry[];
  generatedBlog?: {
    title: string;
    content: string;
    heroImageUrl?: string;
  };
  userStats?: {
    generationsUsed: number;
    generationsLimit: number;
  };
}

export function AgenticChatInterface({
  onGenerateBlog,
  currentJob,
  isGenerating,
  logs,
  generatedBlog,
  userStats
}: AgenticChatInterfaceProps) {
  const [input, setInput] = useState("");
  const [chatHistory, setChatHistory] = useState<Array<{
    type: 'user' | 'assistant' | 'system';
    message: string;
    timestamp: Date;
    metadata?: any;
  }>>([]);
  
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs, chatHistory]);

  // Add system messages for status updates
  useEffect(() => {
    if (currentJob && isGenerating) {
      const latestLog = logs[logs.length - 1];
      if (latestLog && latestLog.message !== "Processing...") {
        setChatHistory(prev => {
          // Avoid duplicates
          const lastMessage = prev[prev.length - 1];
          if (lastMessage?.message === latestLog.message) return prev;
          
          return [...prev, {
            type: 'system',
            message: latestLog.message,
            timestamp: new Date(latestLog.timestamp),
            metadata: { step: latestLog.step, progress: latestLog.progress }
          }];
        });
      }
    }
  }, [logs, currentJob, isGenerating]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isGenerating) return;

    // Add user message to chat
    setChatHistory(prev => [...prev, {
      type: 'user',
      message: input,
      timestamp: new Date()
    }]);

    // Add assistant acknowledgment
    setChatHistory(prev => [...prev, {
      type: 'assistant',
      message: `I'll create a comprehensive blog post about "${input}". Let me start the research and writing process...`,
      timestamp: new Date()
    }]);

    onGenerateBlog(input);
    setInput("");
  };

  const getAgentIcon = (step: string) => {
    if (step.toLowerCase().includes('research')) return '🔍';
    if (step.toLowerCase().includes('content') || step.toLowerCase().includes('draft')) return '✍️';
    if (step.toLowerCase().includes('fact')) return '✅';
    if (step.toLowerCase().includes('final')) return '🎯';
    return '🤖';
  };

  const getStatusColor = (progress: number) => {
    if (progress < 25) return 'bg-blue-500';
    if (progress < 50) return 'bg-yellow-500';
    if (progress < 75) return 'bg-orange-500';
    return 'bg-green-500';
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-white dark:bg-gray-800">
        <div className="flex items-center gap-3">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="bg-gradient-to-r from-blue-500 to-purple-600 text-white">
              <Bot className="h-4 w-4" />
            </AvatarFallback>
          </Avatar>
          <div>
            <h2 className="font-semibold text-lg">AI Blog Generator</h2>
            <p className="text-sm text-gray-500">Multi-agent content creation system</p>
          </div>
        </div>
        
        {userStats && (
          <Badge variant="outline" className="flex items-center gap-1">
            <FileText className="h-3 w-3" />
            {userStats.generationsUsed}/{userStats.generationsLimit} used
          </Badge>
        )}
      </div>

      {/* Chat Area */}
      <ScrollArea className="flex-1 p-4" ref={scrollAreaRef}>
        <div className="space-y-4">
          {/* Welcome Message */}
          {chatHistory.length === 0 && !isGenerating && (
            <div className="text-center py-8">
              <Bot className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <h3 className="text-lg font-medium mb-2">Welcome to AI Blog Generator</h3>
              <p className="text-gray-500 mb-4">
                Enter a topic below and I&apos;ll create a comprehensive, well-researched blog post for you.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 max-w-2xl mx-auto">
                <Card className="p-3 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                      onClick={() => setInput("Latest AI trends in 2025")}>
                  <div className="text-sm font-medium">AI Trends 2025</div>
                  <div className="text-xs text-gray-500">Explore cutting-edge developments</div>
                </Card>
                <Card className="p-3 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                      onClick={() => setInput("Remote work best practices")}>
                  <div className="text-sm font-medium">Remote Work</div>
                  <div className="text-xs text-gray-500">Best practices and tips</div>
                </Card>
                <Card className="p-3 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors"
                      onClick={() => setInput("Sustainable technology solutions")}>
                  <div className="text-sm font-medium">Green Tech</div>
                  <div className="text-xs text-gray-500">Sustainable innovations</div>
                </Card>
              </div>
            </div>
          )}

          {/* Chat Messages */}
          {chatHistory.map((message, index) => (
            <div
              key={index}
              className={cn(
                "flex gap-3",
                message.type === 'user' ? "justify-end" : "justify-start"
              )}
            >
              {message.type !== 'user' && (
                <Avatar className="h-8 w-8">
                  <AvatarFallback className={cn(
                    "text-white",
                    message.type === 'system' 
                      ? "bg-gradient-to-r from-green-500 to-blue-500"
                      : "bg-gradient-to-r from-blue-500 to-purple-600"
                  )}>
                    {message.type === 'system' ? getAgentIcon(message.metadata?.step || '') : <Bot className="h-4 w-4" />}
                  </AvatarFallback>
                </Avatar>
              )}
              
              <div className={cn(
                "max-w-[80%] rounded-lg p-3",
                message.type === 'user'
                  ? "bg-blue-500 text-white"
                  : message.type === 'system'
                  ? "bg-gray-100 dark:bg-gray-700 border-l-4 border-blue-500"
                  : "bg-gray-100 dark:bg-gray-700"
              )}>
                <div className="text-sm">{message.message}</div>
                
                {message.metadata?.progress !== undefined && (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 bg-gray-200 dark:bg-gray-600 rounded-full h-1.5">
                      <div 
                        className={cn("h-1.5 rounded-full transition-all duration-300", getStatusColor(message.metadata.progress))}
                        style={{ width: `${message.metadata.progress}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500">{message.metadata.progress}%</span>
                  </div>
                )}
                
                <div className="flex items-center gap-1 mt-1">
                  <Clock className="h-3 w-3 text-gray-400" />
                  <span className="text-xs text-gray-500">
                    {message.timestamp.toLocaleTimeString()}
                  </span>
                </div>
              </div>

              {message.type === 'user' && (
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-gray-500 text-white">
                    <User className="h-4 w-4" />
                  </AvatarFallback>
                </Avatar>
              )}
            </div>
          ))}

          {/* Loading State */}
          {isGenerating && (
            <div className="flex gap-3">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-gradient-to-r from-blue-500 to-purple-600 text-white">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </AvatarFallback>
              </Avatar>
              <div className="bg-gray-100 dark:bg-gray-700 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                  <span className="text-sm">
                    {currentJob?.currentStep || "Working on your blog post..."}
                  </span>
                </div>
                {currentJob && (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 bg-gray-200 dark:bg-gray-600 rounded-full h-1.5">
                      <div 
                        className={cn("h-1.5 rounded-full transition-all duration-300", getStatusColor(currentJob.progress))}
                        style={{ width: `${currentJob.progress}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500">{currentJob.progress}%</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Generated Blog Result */}
          {generatedBlog && !isGenerating && (
            <div className="flex gap-3">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-gradient-to-r from-green-500 to-blue-500 text-white">
                  <FileText className="h-4 w-4" />
                </AvatarFallback>
              </Avatar>
              <Card className="flex-1 p-4">
                <div className="flex items-center gap-2 mb-3">
                  <FileText className="h-4 w-4 text-green-500" />
                  <span className="font-medium">Blog Generated Successfully!</span>
                </div>
                <h3 className="font-semibold text-lg mb-2">{generatedBlog.title}</h3>
                {generatedBlog.heroImageUrl && (
                  <img 
                    src={generatedBlog.heroImageUrl} 
                    alt="Blog hero" 
                    className="w-full h-48 object-cover rounded-lg mb-3"
                  />
                )}
                <div className="text-sm text-gray-600 dark:text-gray-300 line-clamp-3">
                  {generatedBlog.content.substring(0, 200)}...
                </div>
                <Button className="mt-3" size="sm">
                  View Full Blog
                </Button>
              </Card>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="border-t bg-white dark:bg-gray-800 p-4">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isGenerating ? "Please wait..." : "Enter your blog topic (e.g., 'AI trends in 2025')"}
            disabled={isGenerating}
            className="flex-1"
          />
          <Button 
            type="submit" 
            disabled={!input.trim() || isGenerating}
            className="px-3"
          >
            {isGenerating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
        
        {userStats && (
          <div className="mt-2 text-xs text-gray-500 text-center">
            {userStats.generationsLimit - userStats.generationsUsed} generations remaining this month
          </div>
        )}
      </div>
    </div>
  );
}