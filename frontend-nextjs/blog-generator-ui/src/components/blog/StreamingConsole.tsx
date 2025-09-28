"use client"
import React from 'react';
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { TypewriterText } from "@/components/ui/TypewriterText";
import { 
  Terminal,
  Trash2,
  Copy,
  Download
} from "lucide-react";
import { ConsoleMessage } from '@/hooks/useConsoleMessages';
import { logger } from '@/lib/logger';

interface StreamingConsoleProps {
  messages: ConsoleMessage[];
  isGenerating: boolean;
  onClearMessages: () => void;
  formatTimestamp: (timestamp: string) => string;
  getMessageIcon: (type: string, level: ConsoleMessage['level']) => string;
  getMessageColorClass: (level: ConsoleMessage['level']) => string;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  consoleContainerRef: React.RefObject<HTMLDivElement | null>;
  className?: string;
}

export function StreamingConsole({
  messages,
  isGenerating,
  onClearMessages,
  formatTimestamp,
  getMessageIcon,
  getMessageColorClass,
  messagesEndRef,
  consoleContainerRef,
  className = ""
}: StreamingConsoleProps) {
  // Copy console output to clipboard
  const copyToClipboard = async () => {
    const consoleText = messages.map(msg => 
      `[${formatTimestamp(msg.timestamp)}] ${getMessageIcon(msg.type, msg.level)} ${msg.message}`
    ).join('\n');
    
    try {
      await navigator.clipboard.writeText(consoleText);
      // Could add a toast notification here
    } catch (err) {
      logger.error('Failed to copy streaming console output', err);
    }
  };

  // Download console log as file
  const downloadLog = () => {
    const consoleText = messages.map(msg => 
      `[${formatTimestamp(msg.timestamp)}] [${msg.type.toUpperCase()}] ${msg.message}`
    ).join('\n');
    
    const blob = new Blob([consoleText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `blog-generation-log-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Card className={`p-6 transition-emphasized ${className}`}>
      <div className="space-y-4 animate-lift-up">
        {/* Console Header */}
        <div className="flex items-center justify-between pb-4 border-b border-gray-200 dark:border-gray-700 transition-comfortable">
          <div className="flex items-center gap-2">
            <Terminal className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Real-time Generation Console
            </h3>
            {isGenerating && (
              <Badge variant="secondary" className="animate-glow-pulse bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300">
                ● Live
              </Badge>
            )}
            {!isGenerating && messages.length > 0 && (
              <Badge variant="outline">
                Completed
              </Badge>
            )}
          </div>

          {/* Console Actions */}
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={copyToClipboard}
              disabled={messages.length === 0}
              className="h-8 w-8 p-0 transition-comfortable"
              title="Copy to clipboard"
            >
              <Copy className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={downloadLog}
              disabled={messages.length === 0}
              className="h-8 w-8 p-0 transition-comfortable"
              title="Download log"
            >
              <Download className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearMessages}
              disabled={messages.length === 0 || isGenerating}
              className="h-8 w-8 p-0 text-red-600 hover:text-red-700 hover:bg-red-50 dark:text-red-400 dark:hover:text-red-300 dark:hover:bg-red-950 transition-comfortable"
              title="Clear console"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Console Content Area */}
        <div 
          ref={consoleContainerRef}
          className="bg-gray-900 dark:bg-gray-950 rounded-lg p-4 min-h-[400px] max-h-[500px] overflow-y-auto border-2 border-gray-800 dark:border-gray-700 transition-comfortable"
        >
          {messages.length === 0 ? (
            <div className="text-gray-500 text-center py-8 space-y-2">
              <Terminal className="w-12 h-12 mx-auto mb-4 opacity-30" />
              <p className="text-lg font-medium">Console Ready</p>
              <p className="text-sm">Console output will appear here when you generate a blog.</p>
              <p className="text-xs opacity-75 mt-2">
                Real-time notifications from AI agents will be streamed here, 
                including all {/* Reference to previous 122+ messages */} messages that were previously hidden.
              </p>
            </div>
          ) : (
            <div className="space-y-1 font-mono text-sm">
              {messages.map((msg, index) => {
                const isRecentMessage = index >= messages.length - 10; // Apply typewriter to last 10 messages
                const shouldTypewrite = isRecentMessage && isGenerating;
                const rowAnimationClass = isRecentMessage ? 'animate-fade-in' : '';
                
                return (
                  <div key={msg.id} className={`flex gap-3 leading-relaxed hover:bg-gray-800 dark:hover:bg-gray-900 px-2 py-1 rounded transition-comfortable ${rowAnimationClass}`}>
                    {/* Timestamp */}
                    <span className="text-gray-500 text-xs min-w-[65px] mt-0.5 font-normal">
                      {formatTimestamp(msg.timestamp)}
                    </span>
                    
                    {/* Icon */}
                    <span className="text-sm min-w-[20px] mt-0.5">
                      {getMessageIcon(msg.type, msg.level)}
                    </span>
                    
                    {/* Message Type */}
                    <span className="text-blue-400 text-xs min-w-[80px] mt-0.5 uppercase font-medium">
                      {msg.type}
                    </span>
                    
                    {/* Message Content */}
                    <span className={`flex-1 ${getMessageColorClass(msg.level)}`}>
                      {shouldTypewrite ? (
                        <TypewriterText 
                          text={msg.message}
                          speed={40}
                          className={getMessageColorClass(msg.level)}
                        />
                      ) : (
                        msg.message
                      )}
                    </span>
                  </div>
                );
              })}
              
              {/* Auto-scroll anchor */}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Console Footer Stats */}
        <div className="flex justify-between items-center text-xs text-gray-500 pt-2 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-4">
            <span>Messages: {messages.length}</span>
            {isGenerating && (
              <span className="text-green-500 animate-pulse flex items-center gap-1">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                Streaming live
              </span>
            )}
            {!isGenerating && messages.length > 0 && (
              <span className="text-gray-400">
                Generation completed
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 text-gray-400">
            <span>Auto-scroll enabled</span>
            <span>•</span>
            <span>Console v2.0</span>
          </div>
        </div>
      </div>
    </Card>
  );
}