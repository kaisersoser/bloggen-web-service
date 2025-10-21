/**
 * Timeline Card Component
 * 
 * Expandable card for displaying timeline items (phases, agents, tools).
 * Matches the design from the mockup with status indicators and expandable details.
 */

'use client';

import React from 'react';
import { ChevronDown, ChevronUp, CheckCircle2, Circle, XCircle, Loader2 } from 'lucide-react';
import type { TimelineItem, PhaseItem, AgentItem, ToolItem } from '@/types/timeline';
import { isPhaseItem, isAgentItem, isToolItem } from '@/types/timeline';

interface TimelineCardProps {
  item: TimelineItem;
  onToggleExpand: (itemId: string) => void;
}

/**
 * Get status icon and color based on item status
 */
function getStatusIndicator(status: TimelineItem['status']) {
  switch (status) {
    case 'completed':
      return { icon: CheckCircle2, color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/20' };
    case 'in_progress':
      return { icon: Loader2, color: 'text-blue-500 animate-spin', bg: 'bg-blue-50 dark:bg-blue-900/20' };
    case 'error':
      return { icon: XCircle, color: 'text-red-500', bg: 'bg-red-50 dark:bg-red-900/20' };
    case 'pending':
    default:
      return { icon: Circle, color: 'text-gray-400', bg: 'bg-gray-50 dark:bg-gray-900/20' };
  }
}

/**
 * Format timestamp to readable time
 */
function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit',
    hour12: false 
  });
}

/**
 * Get border color based on item type
 */
function getBorderColor(type: TimelineItem['type']): string {
  switch (type) {
    case 'phase':
      return 'border-purple-500 dark:border-purple-400';
    case 'agent':
      return 'border-blue-500 dark:border-blue-400';
    case 'tool':
      return 'border-orange-500 dark:border-orange-400';
    default:
      return 'border-gray-300 dark:border-gray-600';
  }
}

/**
 * Phase Card - Shows phase progress and overview
 */
function PhaseCard({ item, onToggleExpand }: { item: PhaseItem; onToggleExpand: (id: string) => void }) {
  const { icon: StatusIcon, color, bg } = getStatusIndicator(item.status);
  const borderColor = getBorderColor('phase');
  const pulseEffect = item.status === 'in_progress' ? 'animate-pulse-border' : '';

  return (
    <div
      className={`min-w-[280px] max-w-[280px] rounded-lg border-2 ${borderColor} ${bg} ${pulseEffect}
        transition-all duration-200 hover:shadow-md cursor-pointer`}
      onClick={() => onToggleExpand(item.id)}
    >
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 flex-1">
            <StatusIcon className={`h-5 w-5 ${color}`} />
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100 truncate">
                {item.title}
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {formatTime(item.timestamp)}
              </p>
            </div>
          </div>
          {item.expanded ? (
            <ChevronUp className="h-4 w-4 text-gray-400 flex-shrink-0" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
          )}
        </div>

        {/* Progress bar */}
        {item.progress !== undefined && (
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
              <span>Progress</span>
              <span>{Math.round(item.progress)}%</span>
            </div>
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-purple-500 transition-all duration-300"
                style={{ width: `${item.progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Expandable details */}
      {item.expanded && item.description && (
        <div className="px-4 pb-4 pt-2 border-t border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-700 dark:text-gray-300">{item.description}</p>
        </div>
      )}
    </div>
  );
}

/**
 * Agent Card - Shows agent name, role, and reasoning
 */
function AgentCard({ item, onToggleExpand }: { item: AgentItem; onToggleExpand: (id: string) => void }) {
  const { icon: StatusIcon, color, bg } = getStatusIndicator(item.status);
  const borderColor = getBorderColor('agent');
  const pulseEffect = item.status === 'in_progress' ? 'animate-pulse-border' : '';

  return (
    <div
      className={`min-w-[280px] max-w-[280px] rounded-lg border-2 ${borderColor} ${bg} ${pulseEffect}
        transition-all duration-200 hover:shadow-md cursor-pointer`}
      onClick={() => onToggleExpand(item.id)}
    >
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 flex-1">
            <StatusIcon className={`h-5 w-5 ${color}`} />
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100 truncate">
                {item.title}
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">{item.role}</p>
              <p className="text-xs text-gray-400 dark:text-gray-500">
                {formatTime(item.timestamp)}
              </p>
            </div>
          </div>
          {item.expanded ? (
            <ChevronUp className="h-4 w-4 text-gray-400 flex-shrink-0" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
          )}
        </div>
      </div>

      {/* Expandable details */}
      {item.expanded && (item.reasoning || item.output) && (
        <div className="px-4 pb-4 pt-2 border-t border-gray-200 dark:border-gray-700 space-y-2">
          {item.reasoning && (
            <div>
              <h4 className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Reasoning</h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                {item.reasoning}
              </p>
            </div>
          )}
          {item.output && (
            <div>
              <h4 className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Output</h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap line-clamp-4">
                {item.output}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Tool Card - Shows tool name, status, and output
 */
function ToolCard({ item, onToggleExpand }: { item: ToolItem; onToggleExpand: (id: string) => void }) {
  const { icon: StatusIcon, color, bg } = getStatusIndicator(item.status);
  const borderColor = getBorderColor('tool');
  const pulseEffect = item.status === 'in_progress' ? 'animate-pulse-border' : '';

  return (
    <div
      className={`min-w-[280px] max-w-[280px] rounded-lg border-2 ${borderColor} ${bg} ${pulseEffect}
        transition-all duration-200 hover:shadow-md cursor-pointer`}
      onClick={() => onToggleExpand(item.id)}
    >
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 flex-1">
            <StatusIcon className={`h-5 w-5 ${color}`} />
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-sm text-gray-900 dark:text-gray-100 truncate">
                {item.toolName}
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">Tool</p>
              <p className="text-xs text-gray-400 dark:text-gray-500">
                {formatTime(item.timestamp)}
              </p>
            </div>
          </div>
          {item.expanded ? (
            <ChevronUp className="h-4 w-4 text-gray-400 flex-shrink-0" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400 flex-shrink-0" />
          )}
        </div>
      </div>

      {/* Expandable details */}
      {item.expanded && (item.output || item.error) && (
        <div className="px-4 pb-4 pt-2 border-t border-gray-200 dark:border-gray-700 space-y-2">
          {item.error && (
            <div>
              <h4 className="text-xs font-medium text-red-600 dark:text-red-400 mb-1">Error</h4>
              <p className="text-sm text-red-700 dark:text-red-300 whitespace-pre-wrap">
                {item.error}
              </p>
            </div>
          )}
          {item.output && !item.error && (
            <div>
              <h4 className="text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Output</h4>
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap line-clamp-4">
                {item.output}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Main TimelineCard component - routes to appropriate card type
 */
export function TimelineCard({ item, onToggleExpand }: TimelineCardProps) {
  // Add fade-in animation for new items
  const cardClasses = "animate-in fade-in slide-in-from-left-4 duration-300";

  if (isPhaseItem(item)) {
    return (
      <div className={cardClasses}>
        <PhaseCard item={item} onToggleExpand={onToggleExpand} />
      </div>
    );
  }

  if (isAgentItem(item)) {
    return (
      <div className={cardClasses}>
        <AgentCard item={item} onToggleExpand={onToggleExpand} />
      </div>
    );
  }

  if (isToolItem(item)) {
    return (
      <div className={cardClasses}>
        <ToolCard item={item} onToggleExpand={onToggleExpand} />
      </div>
    );
  }

  return null;
}
