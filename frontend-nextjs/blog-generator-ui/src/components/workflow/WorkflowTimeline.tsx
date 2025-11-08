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
import type { TimelineState, TimelineItem } from '@/types/timeline';
import type { LogEntry } from '@/types/blog';
import type { SSEEvent } from '@/types/workflow-graph';

interface WorkflowTimelineProps {
  taskId: string;
  taskLogs?: LogEntry[];  // Receive logs from parent instead of creating SSE connection
  enableDebugLogging?: boolean;
}

/**
 * Convert LogEntry to SSEEvent format for timeline parser
 */
function convertLogToSSEEvent(log: LogEntry): SSEEvent | null {
  // Determine event type from message content
  let eventType: SSEEvent['type'] = 'log';
  
  const msgLower = log.message.toLowerCase();
  
  // Detect connection events
  if (msgLower.includes('blog generation started') || 
      msgLower.includes('setting up connection') ||
      msgLower.includes('live updates connected')) {
    eventType = 'status';
  } else if (msgLower.includes('phase in progress') || 
             msgLower.includes('completed') || 
             msgLower.includes('status:')) {
    eventType = 'status';
  } else if (log.message.includes('💭')) {
    eventType = 'agent_thinking';
  } else if (log.message.includes('🔧')) {
    eventType = 'tool_usage';
  }

  // Extract agent name from thinking messages
  const agentMatch = log.message.match(/💭\s*([A-Z][a-z\s]+?)(?:\s+(?:returned|completed|ready|starting|beginning))/i);
  
  // Extract tool name from tool messages
  const toolMatch = log.message.match(/🔧\s*(?:Executing|Using)?\s*([a-z_]+)/i);

  return {
    type: eventType,
    data: {
      task_id: '',  // LogEntry doesn't have taskId
      status: log.step,  // Use step field as status
      message: log.message,
      timestamp: log.timestamp,
      progress: extractProgress(log.message) || log.progress,
      agent_name: agentMatch ? agentMatch[1].trim() : undefined,
      reasoning: eventType === 'agent_thinking' ? log.message.replace('💭', '').trim() : undefined,
      tool_name: toolMatch ? toolMatch[1].trim() : undefined,
    }
  };
}

/**
 * Extract progress percentage from message
 */
function extractProgress(message: string): number | undefined {
  // Look for percentage in message
  const match = message.match(/(\d+)%/);
  if (match) {
    return parseInt(match[1], 10);
  }
  
  // Infer progress from phase messages
  if (message.toLowerCase().includes('research') && message.toLowerCase().includes('progress')) return 25;
  if (message.toLowerCase().includes('content') && message.toLowerCase().includes('progress')) return 50;
  if (message.toLowerCase().includes('fact') || message.toLowerCase().includes('validation')) return 75;
  if (message.toLowerCase().includes('finalization') && message.toLowerCase().includes('progress')) return 90;
  if (message.toLowerCase().includes('completed') || message.toLowerCase().includes('complete')) return 100;
  
  return undefined;
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
export function WorkflowTimeline({ taskId, taskLogs = [], enableDebugLogging = false }: WorkflowTimelineProps) {
  const [timeline, setTimeline] = useState<TimelineState>({
    items: [],
    currentPhase: null,
    overallProgress: 0,
    startTime: new Date().toISOString(),
    isComplete: false,
  });

  // Timeline parser instance (persisted across renders)
  const parserRef = useRef(new TimelineParser(enableDebugLogging));
  const timelineContainerRef = useRef<HTMLDivElement>(null);
  const lastProcessedIndex = useRef(0);

  /**
   * Process task logs from parent component
   */
  useEffect(() => {
    console.log('📅 [WorkflowTimeline] useEffect triggered:', {
      hasTaskLogs: !!taskLogs,
      taskLogsLength: taskLogs?.length || 0,
      lastProcessed: lastProcessedIndex.current,
      currentItemsCount: timeline.items.length,
      isComplete: timeline.isComplete
    });

    if (!taskLogs || taskLogs.length === 0) {
      console.log('⚠️ [WorkflowTimeline] No taskLogs, skipping');
      return;
    }

    // Only process new logs
    const newLogs = taskLogs.slice(lastProcessedIndex.current);
    if (newLogs.length === 0) {
      console.log('⚠️ [WorkflowTimeline] No new logs to process');
      return;
    }

    console.log('� [WorkflowTimeline] Processing new logs:', {
      total: taskLogs.length,
      newCount: newLogs.length,
      lastProcessed: lastProcessedIndex.current,
      firstNewLog: newLogs[0]?.message.substring(0, 50)
    });

    // Convert LogEntry to SSE events and process
    let eventsProcessed = 0;
    newLogs.forEach((log, index) => {
      console.log(`📋 [WorkflowTimeline] Processing log ${lastProcessedIndex.current + index}:`, log.message.substring(0, 80));
      
      const sseEvent = convertLogToSSEEvent(log);
      if (sseEvent) {
        console.log(`  ↳ Converted to SSE event:`, sseEvent.type, sseEvent.data.message?.substring(0, 50));
        
        // Check if this is a completion event
        const isCompletionEvent = 
          sseEvent.type === 'status' && 
          (sseEvent.data.status?.toLowerCase().includes('complete') || 
           sseEvent.data.message?.toLowerCase().includes('complete'));

        parserRef.current.processEvent(sseEvent);
        eventsProcessed++;

        // If completion event, mark timeline as complete
        if (isCompletionEvent && sseEvent.data.progress === 100) {
          console.log('✅ [WorkflowTimeline] Blog generation complete, marking timeline');
          parserRef.current.complete();
        }
      } else {
        console.log(`  ↳ Failed to convert log`);
      }
    });

    // Update state
    const newState = parserRef.current.getState();
    console.log('📊 [WorkflowTimeline] Updating timeline state:', {
      eventsProcessed,
      newItemsCount: newState.items.length,
      previousItemsCount: timeline.items.length
    });
    
    setTimeline(newState);
    lastProcessedIndex.current = taskLogs.length;

    // Auto-scroll to the end
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
  }, [taskLogs, enableDebugLogging, timeline.items.length, timeline.isComplete]);

  // Remove old SSE hook code  
  // const { isConnected } = useWorkflowSSE({
  //   taskId,
  //   onEvent: handleSSEEvent,
  //   enabled: true,
  // });

  // Reset timeline when taskId changes ONLY if not complete
  useEffect(() => {
    console.log('🔄 [WorkflowTimeline] TaskId effect triggered:', { 
      taskId, 
      isComplete: timeline.isComplete,
      itemCount: timeline.items.length 
    });
    
    // Don't reset if timeline is complete OR if we have items (to prevent clearing during generation)
    if (!timeline.isComplete && timeline.items.length === 0) {
      console.log('🔄 [WorkflowTimeline] Resetting timeline for new task (empty timeline)');
      parserRef.current.reset();
      lastProcessedIndex.current = 0;
      setTimeline({
        items: [],
        currentPhase: null,
        overallProgress: 0,
        startTime: new Date().toISOString(),
        isComplete: false,
      });
    } else {
      console.log('✅ [WorkflowTimeline] Preserving timeline state:', {
        reason: timeline.isComplete ? 'completed' : 'has items',
        itemCount: timeline.items.length
      });
    }
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
  const isConnected = taskLogs && taskLogs.length > 0;

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
