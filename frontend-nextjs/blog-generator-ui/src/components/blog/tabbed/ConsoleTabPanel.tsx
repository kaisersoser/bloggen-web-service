"use client";

import React from "react";
import { Card } from "@/components/ui/card";
import { SSEConnectionStatus } from "@/components/ui/SSEConnectionStatus";
import dynamic from "next/dynamic";
import type { ConsoleMessage } from "@/hooks/useConsoleMessages";
import type { RefObject } from "react";

const StreamingConsole = dynamic(
  () => import('@/components/blog/StreamingConsole').then((mod) => mod.StreamingConsole),
  {
    ssr: false,
    loading: () => (
      <div className="bg-gray-900 dark:bg-gray-950 rounded-lg p-6 border border-gray-800 dark:border-gray-700">
        <div className="flex items-center justify-between pb-4 border-b border-gray-800">
          <div className="h-5 w-40 bg-gray-800 animate-pulse rounded" />
          <div className="h-8 w-24 bg-gray-800 animate-pulse rounded" />
        </div>
        <div className="space-y-2 mt-4">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="h-10 bg-gray-800/70 animate-pulse rounded" />
          ))}
        </div>
      </div>
    ),
  }
);

interface ConsoleTabPanelProps {
  messages: ConsoleMessage[];
  isGenerating: boolean;
  clearMessages: () => void;
  formatTimestamp: (timestamp: string) => string;
  getMessageIcon: (type: string, level: ConsoleMessage['level']) => string;
  getMessageColorClass: (level: ConsoleMessage['level']) => string;
  messagesEndRef: RefObject<HTMLDivElement | null>;
  consoleContainerRef: RefObject<HTMLDivElement | null>;
  connectionStatus?: {
    status: 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'offline_wait' | 'closed' | 'error';
    message?: string | null;
    updatedAt?: string | null;
  } | null;
}

export function ConsoleTabPanel({
  messages,
  isGenerating,
  clearMessages,
  formatTimestamp,
  getMessageIcon,
  getMessageColorClass,
  messagesEndRef,
  consoleContainerRef,
  connectionStatus,
}: ConsoleTabPanelProps) {
  const shouldShowConnectionStatus =
    connectionStatus && (isGenerating || connectionStatus.status !== 'closed');

  return (
    <div className="space-y-4">
      {shouldShowConnectionStatus && (
        <SSEConnectionStatus
          status={connectionStatus.status}
          message={connectionStatus.message ?? undefined}
          updatedAt={connectionStatus.updatedAt ?? undefined}
        />
      )}
      <Card className="p-6 transition-emphasized surface-elevated animate-soft-pop">
        <StreamingConsole
          messages={messages}
          isGenerating={isGenerating}
          onClearMessages={clearMessages}
          formatTimestamp={formatTimestamp}
          getMessageIcon={getMessageIcon}
          getMessageColorClass={getMessageColorClass}
          messagesEndRef={messagesEndRef}
          consoleContainerRef={consoleContainerRef}
        />
      </Card>
    </div>
  );
}
