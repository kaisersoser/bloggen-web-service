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
import { FileText, Terminal, Workflow } from "lucide-react";
import dynamic from "next/dynamic";

// Lazy load WorkflowTimeline to avoid SSR issues
const WorkflowTimeline = dynamic(
  () => import("@/components/workflow/WorkflowTimeline").then(mod => ({ default: mod.WorkflowTimeline })),
  { 
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center">
        <div className="animate-pulse text-gray-500">Loading workflow...</div>
      </div>
    )
  }
);

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

  // Restore tab preference from localStorage
  useEffect(() => {
    const savedTab = localStorage.getItem('bloggen_preferred_view_tab');
    if (savedTab && ['instructions', 'console', 'workflow'].includes(savedTab)) {
      setActiveTab(savedTab);
    }
  }, []);

  // Persist tab preference to localStorage
  useEffect(() => {
    localStorage.setItem('bloggen_preferred_view_tab', activeTab);
  }, [activeTab]);

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

  // Keyboard shortcut: Space = toggle between workflow and console
  useEffect(() => {
    const handleKeyPress = (event: globalThis.KeyboardEvent) => {
      // Only trigger if not typing in an input/textarea
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        return;
      }
      
      if (event.key === ' ' && currentJobId) {
        event.preventDefault();
        setActiveTab(prev => prev === 'workflow' ? 'console' : 'workflow');
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [currentJobId]);

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

      {(isGenerating || hasStreamingContent) && (
        <DraftPreviewDialog
          isOpen={isDraftModalOpen}
          onOpenChange={setIsDraftModalOpen}
          streamingContent={streamingContent}
          isGenerating={isGenerating}
        />
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3 rounded-xl bg-gradient-to-r from-slate-900/5 via-white to-slate-900/5 dark:from-slate-500/10 dark:via-slate-900 dark:to-slate-500/10 p-1 shadow-sm transition-comfortable">
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
          <TabsTrigger
            value="workflow"
            className="group flex items-center gap-2 rounded-lg transition-comfortable focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/70 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-slate-900 data-[state=active]:bg-white data-[state=active]:text-gray-900 data-[state=active]:shadow-sm dark:data-[state=active]:bg-slate-800/80 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={!currentJobId}
          >
            <Workflow className="h-4 w-4" />
            Visual Flow
            {isGenerating && (
              <Badge
                variant="secondary"
                className="ml-1 text-xs bg-purple-100 text-purple-800 animate-pulse"
              >
                Live
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

        <TabsContent value="workflow" className="space-y-4 animate-lift-up">
          {currentJobId ? (
            <div className="w-full h-[600px] rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden shadow-sm">
              <WorkflowTimeline 
                taskId={currentJobId}
                taskLogs={taskLogs?.[currentJobId] || []}
                enableDebugLogging={process.env.NODE_ENV === 'development'}
              />
            </div>
          ) : (
            <div className="w-full h-[600px] rounded-lg border border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/50 flex flex-col items-center justify-center text-center p-8">
              <Workflow className="h-16 w-16 text-gray-400 dark:text-gray-500 mb-4" />
              <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
                No Active Workflow
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md">
                Start generating a blog to see the live visualization of the AI workflow. 
                Watch agents collaborate in real-time!
              </p>
              <div className="mt-6 flex items-center gap-2 text-xs text-gray-400">
                <kbd className="px-2 py-1 rounded bg-gray-200 dark:bg-gray-700 font-mono">Space</kbd>
                <span>Toggle between Console and Visual Flow</span>
              </div>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};