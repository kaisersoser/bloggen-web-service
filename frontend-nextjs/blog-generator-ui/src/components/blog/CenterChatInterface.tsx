"use client"
import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { 
  Send, 
  Sparkles, 
  Loader2, 
  Zap, 
  Brain,
  Lightbulb,
  Target,
  Clock
} from "lucide-react";

interface CenterChatInterfaceProps {
  onSubmit: (prompt: string) => void;
  isGenerating?: boolean;
  disabled?: boolean;
  remainingGenerations?: number;
  userRole?: 'FREE' | 'PREMIUM' | 'ADMIN';
  className?: string;
}

export function CenterChatInterface({ 
  onSubmit, 
  isGenerating = false, 
  disabled = false,
  remainingGenerations,
  userRole = 'FREE',
  className = "" 
}: CenterChatInterfaceProps) {
  const [prompt, setPrompt] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim() && !isGenerating && !disabled) {
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

  const getRoleIcon = () => {
    switch (userRole) {
      case 'ADMIN':
        return <Zap className="w-4 h-4 text-yellow-500" />;
      case 'PREMIUM':
        return <Brain className="w-4 h-4 text-purple-500" />;
      default:
        return <Lightbulb className="w-4 h-4 text-blue-500" />;
    }
  };

  const getRoleBadge = () => {
    const badges = {
      ADMIN: { text: 'Admin', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' },
      PREMIUM: { text: 'Premium', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
      FREE: { text: 'Free', color: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200' }
    };
    
    const badge = badges[userRole];
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
        {getRoleIcon()}
        {badge.text}
      </span>
    );
  };

  const isAtLimit = userRole !== 'ADMIN' && remainingGenerations !== undefined && remainingGenerations <= 0;

  return (
    <div className={`w-full max-w-4xl mx-auto ${className}`}>
      {/* Header Section */}
      <div className="text-center mb-6">
        <div className="inline-flex items-center gap-2 mb-4">
          <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            AI Blog Generator
          </h1>
        </div>
        <p className="text-gray-600 dark:text-gray-400 text-lg mb-4">
          Transform your ideas into engaging, well-researched blog posts with AI-powered content generation
        </p>
        
        {/* User Stats */}
        <div className="flex items-center justify-center gap-4 text-sm">
          {getRoleBadge()}
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

      {/* Chat Interface */}
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
                  AI agents are collaborating to create your blog...
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
    </div>
  );
}
