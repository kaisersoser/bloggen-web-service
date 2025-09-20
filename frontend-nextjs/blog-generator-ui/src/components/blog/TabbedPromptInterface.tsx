"use client"
import React, { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { StreamingConsole } from "./StreamingConsole";
import { useConsoleMessages } from "@/hooks/useConsoleMessages";
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
  FileText
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

  // Auto-switch to console tab when generation starts
  React.useEffect(() => {
    if (isGenerating && activeTab === 'instructions') {
      setActiveTab('console');
    }
  }, [isGenerating, activeTab]);

  // Convert taskLogs to console messages
  React.useEffect(() => {
    if (currentJobId && taskLogs[currentJobId]) {
      const logs = taskLogs[currentJobId];
      const currentMessageCount = messages.length;
      
      console.log('📊 TaskLogs processing:', {
        currentJobId,
        logsCount: logs.length,
        currentMessageCount
      });
      
      // Only process new messages that aren't already in the console
      if (logs.length > currentMessageCount) {
        const newLogs = logs.slice(currentMessageCount);
        
        console.log('✅ Processing new logs:', {
          newLogsCount: newLogs.length
        });
        
        // Process all new messages
        newLogs.forEach((log) => {
          console.log('➕ Adding message:', log.message);
          addMessage(
            log.step || 'info',
            log.message,
            { progress: log.progress, timestamp: log.timestamp },
            'info'
          );
        });
      }
    }
  }, [taskLogs, currentJobId, addMessage, messages.length]);

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