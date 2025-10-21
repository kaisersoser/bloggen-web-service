/**
 * Workflow Timeline Component
 * 
 * Linear timeline visualization for AI blog generation workflow.
 * Simple horizontal scroll layout with connecting arrows - no complex graph library needed.
 */

'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { ArrowRight, Zap } from 'lucide-react';
import { TimelineCard } from './TimelineCard';
import { TimelineParser } from '@/lib/timeline-parser';
import { useWorkflowSSE } from '@/hooks/useWorkflowSSE';
import type { TimelineState, TimelineItem } from '@/types/timeline';
import type { SSEEvent } from '@/types/workflow-graph';

interface WorkflowTimelineProps {
  taskId: string;
  enableDebugLogging?: boolean;
}

/**
 * Connecting arrow between timeline items
 */
function ConnectingArrow() {
  return (
    <div className="flex items-center justify-center flex-shrink-0 px-4">
      <ArrowRight className="h-6 w-6 text-gray-400 dark:text-gray-600" />
    </div>
  );
}

/**
 * Main Timeline component
 */
export function WorkflowTimeline({ taskId, enableDebugLogging = false }: WorkflowTimelineProps) {
  const [timeline, setTimeline] = useState<TimelineState>({
    items: [],
    currentPhase: null,
    overallProgress: 0,
    startTime: new Date().toISOString(),
  });

  // Timeline parser instance (persisted across renders)
  const parserRef = useRef(new TimelineParser(enableDebugLogging));
  const timelineContainerRef = useRef<HTMLDivElement>(null);

  /**
   * Handle SSE events and update timeline
   */
  const handleSSEEvent = useCallback((event: SSEEvent) => {
    if (enableDebugLogging) {
      console.log('📅 [WorkflowTimeline] Received SSE event:', event.type);
    }

    const updatedTimeline = parserRef.current.processEvent(event);
    setTimeline(updatedTimeline);

    // Auto-scroll to the end when new items are added
    if (timelineContainerRef.current) {
      setTimeout(() => {
        if (timelineContainerRef.current) {
          timelineContainerRef.current.scrollTo({
            left: timelineContainerRef.current.scrollWidth,
            behavior: 'smooth',
          });
        }
      }, 100);
    }
  }, [enableDebugLogging]);

  // Connect to SSE stream
  const { isConnected } = useWorkflowSSE({
    taskId,
    onEvent: handleSSEEvent,
    enabled: true,
  });

  // Reset timeline when taskId changes
  useEffect(() => {
    console.log('🔄 [WorkflowTimeline] TaskId changed, resetting timeline:', taskId);
    parserRef.current.reset();
    setTimeline({
      items: [],
      currentPhase: null,
      overallProgress: 0,
      startTime: new Date().toISOString(),
    });
  }, [taskId]);

  /**
   * Toggle expand/collapse for an item
   */
  const handleToggleExpand = useCallback((itemId: string) => {
    setTimeline((prev) => ({
      ...prev,
      items: prev.items.map((item) =>
        item.id === itemId ? { ...item, expanded: !item.expanded } : item
      ),
    }));
  }, []);

  // Empty state
  if (timeline.items.length === 0) {
    return (
      <div className="h-full w-full flex items-center justify-center">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-800 mb-4">
            <Zap className="h-8 w-8 text-gray-400 dark:text-gray-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Waiting for workflow events...
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {isConnected ? 'Connected to live stream' : 'Connecting...'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col bg-gray-50 dark:bg-gray-900/50">
      {/* Header with progress */}
      <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {timeline.currentPhase || 'Initializing...'}
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {timeline.items.length} {timeline.items.length === 1 ? 'event' : 'events'} logged
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {Math.round(timeline.overallProgress)}%
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">Progress</p>
            </div>
            <div className="w-32 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-300"
                style={{ width: `${timeline.overallProgress}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Scrollable timeline */}
      <div
        ref={timelineContainerRef}
        className="flex-1 overflow-x-auto overflow-y-hidden"
      >
        <div className="inline-flex items-center min-h-full p-6 gap-0">
          {timeline.items.map((item, index) => (
            <React.Fragment key={item.id}>
              <TimelineCard item={item} onToggleExpand={handleToggleExpand} />
              {index < timeline.items.length - 1 && <ConnectingArrow />}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Debug panel */}
      {enableDebugLogging && (
        <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 bg-black text-white p-3 text-xs font-mono">
          <div>Items: {timeline.items.length}</div>
          <div>Phase: {timeline.currentPhase || 'none'}</div>
          <div>Progress: {Math.round(timeline.overallProgress)}%</div>
          <div>Connected: {isConnected ? 'yes' : 'no'}</div>
        </div>
      )}
    </div>
  );
}
