"use client";

import React, { FormEvent, KeyboardEvent, useMemo, useState } from "react";
import { PromptInstructionsPanel } from "@/components/blog/tabbed/PromptInstructionsPanel";
import { TabbedPromptHeader } from "@/components/blog/tabbed/TabbedPromptHeader";
import type { LogEntry } from "@/types/blog";

interface TabbedPromptInterfaceProps {
  onSubmit: (prompt: string) => void;
  isGenerating?: boolean;
  disabled?: boolean;
  remainingGenerations?: number;
  userRole?: 'FREE' | 'PREMIUM' | 'ADMIN';
  className?: string;
  taskLogs?: Record<string, LogEntry[]>;
  currentJobId?: string | null;
  clearTaskLogs?: () => void;
  connectionStatus?: {
    status: 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'offline_wait' | 'closed' | 'error';
    message?: string | null;
    updatedAt?: string | null;
  } | null;
}

export const TabbedPromptInterface = ({
  onSubmit,
  isGenerating = false,
  disabled = false,
  remainingGenerations = 0,
  userRole = "FREE",
  className = "",
}: TabbedPromptInterfaceProps) => {
  const [prompt, setPrompt] = useState("");
  const [isFocused, setIsFocused] = useState(false);

  const containerClasses = useMemo(
    () => `w-full max-w-4xl mx-auto space-y-6 ${className}`.trim(),
    [className]
  );

  const triggerSubmission = () => {
    if (!prompt.trim() || isGenerating || disabled) {
      return;
    }

    onSubmit(prompt.trim());
    setPrompt("");
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    triggerSubmission();
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      triggerSubmission();
    }
  };

  const handlePromptChange = (value: string) => {
    setPrompt(value);
  };

  const handleFocusChange = (focused: boolean) => {
    setIsFocused(focused);
  };

  // ADMIN and PREMIUM users with -1 remaining (unlimited) should never be at limit
  const isAtLimit =
    userRole !== "ADMIN" &&
    remainingGenerations !== undefined &&
    remainingGenerations !== -1 &&
    remainingGenerations <= 0;

  return (
    <div className={containerClasses}>
      <TabbedPromptHeader
        remainingGenerations={remainingGenerations}
        userRole={userRole}
      />

      <PromptInstructionsPanel
        prompt={prompt}
        onPromptChange={handlePromptChange}
        onSubmit={handleSubmit}
        onKeyDown={handleKeyDown}
        onFocusChange={handleFocusChange}
        isFocused={isFocused}
        isGenerating={isGenerating}
        disabled={disabled}
        isAtLimit={isAtLimit}
        remainingGenerations={remainingGenerations}
        userRole={userRole}
      />
    </div>
  );
};