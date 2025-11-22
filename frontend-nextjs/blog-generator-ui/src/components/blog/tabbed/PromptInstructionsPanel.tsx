"use client";

import React, { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Send, Clock, Wand2 } from "lucide-react";

type UserRole = "FREE" | "PREMIUM" | "ADMIN";

interface PromptInstructionsPanelProps {
  prompt: string;
  onPromptChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
  onKeyDown: (event: React.KeyboardEvent) => void;
  onFocusChange: (focused: boolean) => void;
  isFocused: boolean;
  isGenerating: boolean;
  disabled: boolean;
  isAtLimit: boolean;
  remainingGenerations?: number;
  userRole: UserRole;
}

export function PromptInstructionsPanel({
  prompt,
  onPromptChange,
  onSubmit,
  onKeyDown,
  onFocusChange,
  isFocused,
  isGenerating,
  disabled,
  isAtLimit,
  remainingGenerations,
  userRole,
}: PromptInstructionsPanelProps) {
  const textareaId = useId();
  const [isGeneratingTopic, setIsGeneratingTopic] = useState(false);

  const handleFeelingLucky = async () => {
    setIsGeneratingTopic(true);
    
    try {
      // Get JWT token for API authentication
      const tokenResponse = await fetch('/api/auth/jwt-token');
      if (!tokenResponse.ok) {
        throw new Error('Failed to get authentication token');
      }
      const { token } = await tokenResponse.json();
      
      // Call backend API to generate random topic
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/generate-random-topic`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate topic');
      }
      
      const data = await response.json();
      onPromptChange(data.topic);
    } catch (error) {
      console.error('Error generating random topic:', error);
      // Fallback to a simple predefined topic if API fails
      const fallbackTopics = [
        "The evolution of artificial intelligence in creative industries",
        "Sustainable business practices reshaping corporate culture",
        "The science behind habit formation and behavioral change",
        "Remote work productivity strategies for distributed teams",
        "Renewable energy innovations powering the future",
      ];
      const randomTopic = fallbackTopics[Math.floor(Math.random() * fallbackTopics.length)];
      onPromptChange(randomTopic);
    } finally {
      setIsGeneratingTopic(false);
    }
  };

  const isSubmitDisabled =
    !prompt.trim() || isGenerating || disabled || isAtLimit;

  return (
    <Card
      className={`p-6 transition-comfortable ${
        isFocused
          ? 'ring-2 ring-blue-500/80 surface-elevated animate-soft-pop'
          : 'shadow-md'
      } ${
        isGenerating
          ? 'ring-2 ring-blue-400/70 animate-glow-pulse'
          : ''
      }`}
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="relative">
          <Textarea
            id={textareaId}
            value={prompt}
            onChange={(event) => onPromptChange(event.target.value)}
            onKeyDown={onKeyDown}
            onFocus={() => onFocusChange(true)}
            onBlur={() => onFocusChange(false)}
            placeholder="Describe the blog topic you'd like to generate... (e.g., 'Latest trends in sustainable technology', 'How to build a productive morning routine', 'The future of remote work')"
            className="min-h-[120px] text-base resize-none pr-16 leading-relaxed transition-comfortable focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/70 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900"
            disabled={disabled || isGenerating || isAtLimit}
          />

          <div className="absolute bottom-3 right-3 flex items-end gap-2">
            <span className="text-xs text-gray-400">{prompt.length}/500</span>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitDisabled}
              className="h-8 w-8 p-0 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-comfortable"
            >
              {isGenerating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            onClick={handleFeelingLucky}
            disabled={isGenerating || disabled || isAtLimit || isGeneratingTopic}
            variant="outline"
            size="sm"
            className="flex items-center gap-2 bg-gradient-to-r from-purple-50 to-blue-50 hover:from-purple-100 hover:to-blue-100 dark:from-purple-900/20 dark:to-blue-900/20 dark:hover:from-purple-900/30 dark:hover:to-blue-900/30 border-purple-200 dark:border-purple-800 text-purple-700 dark:text-purple-300 transition-comfortable disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGeneratingTopic ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Wand2 className="w-4 h-4" />
            )}
            <span>Inspire Me</span>
          </Button>
          {typeof remainingGenerations === 'number' && !isAtLimit && (
            <div className="ml-auto flex items-center gap-1 text-xs text-gray-400 transition-comfortable">
              <Clock className="w-3 h-3" />
              <span>{remainingGenerations} left this month</span>
            </div>
          )}
        </div>

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

        <div className="text-xs text-gray-400 text-center">
          <kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs">Cmd+Enter</kbd> to submit
        </div>
      </form>
    </Card>
  );
}
