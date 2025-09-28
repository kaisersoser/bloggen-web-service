"use client";

import React, { FormEvent, KeyboardEvent, useEffect, useMemo, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ConsoleTabPanel } from "@/components/blog/tabbed/ConsoleTabPanel";
import { DraftPreviewDialog } from "@/components/blog/tabbed/DraftPreviewDialog";
import { PromptInstructionsPanel } from "@/components/blog/tabbed/PromptInstructionsPanel";
import { TabbedPromptHeader } from "@/components/blog/tabbed/TabbedPromptHeader";
import { useGenerationConsoleBridge } from "@/hooks/useGenerationConsoleBridge";
import type { LogEntry } from "@/types/blog";
import { FileText, Terminal } from "lucide-react";

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
  taskLogs,
  currentJobId = null,
  clearTaskLogs,
  connectionStatus = null,
}: TabbedPromptInterfaceProps) => {
  const [prompt, setPrompt] = useState("");
  const [activeTab, setActiveTab] = useState("instructions");
  const [isFocused, setIsFocused] = useState(false);
  const [isDraftModalOpen, setIsDraftModalOpen] = useState(false);

  const containerClasses = useMemo(
    () => `w-full max-w-4xl mx-auto space-y-6 ${className}`.trim(),
    [className]
  );

  const {
    messages,
    streamingContent,
    clearMessages,
    prepareForNewGeneration,
    formatTimestamp,
    getMessageIcon,
    getMessageColorClass,
    messagesEndRef,
    consoleContainerRef,
  } = useGenerationConsoleBridge({
    taskLogs,
    currentJobId,
    isGenerating,
    clearTaskLogs,
  });

  useEffect(() => {
    if (isGenerating && activeTab === "instructions") {
      setActiveTab("console");
    }
  }, [isGenerating, activeTab]);

  const hasStreamingContent =
    Boolean(streamingContent.content_preview) ||
    streamingContent.research_findings.length > 0 ||
    streamingContent.content_paragraphs.length > 0 ||
    streamingContent.fact_corrections.length > 0;

  const triggerSubmission = () => {
    if (!prompt.trim() || isGenerating || disabled) {
      return;
    }

    prepareForNewGeneration();
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

  const isAtLimit =
    remainingGenerations !== undefined &&
    remainingGenerations <= 0 &&
    userRole !== "ADMIN";

  return (
    <div className={containerClasses}>
      <TabbedPromptHeader
        remainingGenerations={remainingGenerations}
        userRole={userRole}
      />

      {(isGenerating || hasStreamingContent) && (
        <DraftPreviewDialog
          isOpen={isDraftModalOpen}
          onOpenChange={setIsDraftModalOpen}
          streamingContent={streamingContent}
          isGenerating={isGenerating}
        />
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-2 rounded-xl bg-gradient-to-r from-slate-900/5 via-white to-slate-900/5 dark:from-slate-500/10 dark:via-slate-900 dark:to-slate-500/10 p-1 shadow-sm transition-comfortable">
          <TabsTrigger
            value="instructions"
            className="group flex items-center gap-2 rounded-lg transition-comfortable focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/70 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900 data-[state=active]:bg-white data-[state=active]:text-gray-900 data-[state=active]:shadow-sm dark:data-[state=active]:bg-slate-800/80"
          >
            <FileText className="h-4 w-4" />
            Instructions
          </TabsTrigger>
          <TabsTrigger
            value="console"
            className="group flex items-center gap-2 rounded-lg transition-comfortable focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/70 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900 data-[state=active]:bg-white data-[state=active]:text-gray-900 data-[state=active]:shadow-sm dark:data-[state=active]:bg-slate-800/80"
          >
            <Terminal className="h-4 w-4" />
            Console
            {messages.length > 0 && (
              <Badge
                variant="secondary"
                className="ml-1 text-xs bg-blue-100 text-blue-800 animate-soft-pop"
              >
                {messages.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="instructions" className="space-y-4 animate-lift-up">
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
        </TabsContent>

        <TabsContent value="console" className="space-y-4 animate-lift-up">
          <ConsoleTabPanel
            messages={messages}
            isGenerating={isGenerating}
            clearMessages={clearMessages}
            formatTimestamp={formatTimestamp}
            getMessageIcon={getMessageIcon}
            getMessageColorClass={getMessageColorClass}
            messagesEndRef={messagesEndRef}
            consoleContainerRef={consoleContainerRef}
            connectionStatus={connectionStatus}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
};