"use client";

import React, { useId } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Send, Clock } from "lucide-react";

type UserRole = "FREE" | "PREMIUM" | "ADMIN";

const SUGGESTIONS = [
  "AI and machine learning trends",
  "Sustainable business practices",
  "Remote work productivity tips",
  "Digital marketing strategies",
];

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

  const handleSuggestionClick = (suggestion: string) => {
    onPromptChange(suggestion);
  };

  const isSubmitDisabled =
    !prompt.trim() || isGenerating || disabled || isAtLimit;

  return (
    <Card
      className={`p-6 transition-all duration-300 ${
        isFocused ? 'ring-2 ring-blue-500 shadow-lg' : 'shadow-md'
      } ${isGenerating ? 'ring-2 ring-blue-400 animate-pulse' : ''}`}
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
            className="min-h-[120px] text-base resize-none pr-16 leading-relaxed"
            disabled={disabled || isGenerating || isAtLimit}
          />

          <div className="absolute bottom-3 right-3 flex items-end gap-2">
            <span className="text-xs text-gray-400">{prompt.length}/500</span>
            <Button
              type="submit"
              size="sm"
              disabled={isSubmitDisabled}
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

        <div className="flex flex-wrap gap-2">
          <span className="text-sm text-gray-500 dark:text-gray-400 mr-2">Try:</span>
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => handleSuggestionClick(suggestion)}
              disabled={isGenerating || disabled || isAtLimit}
              className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {suggestion}
            </button>
          ))}
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
