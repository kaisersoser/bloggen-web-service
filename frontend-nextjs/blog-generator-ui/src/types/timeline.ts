/**
 * Timeline Visualization Types
 * 
 * Simplified data structures for linear workflow visualization
 * Alternative to complex graph structures used by React Flow
 */

export type TimelineItemType = 'phase' | 'agent' | 'tool';
export type TimelineItemStatus = 'pending' | 'in_progress' | 'completed' | 'error';

/**
 * Base timeline item interface
 */
export interface TimelineItem {
  id: string;
  type: TimelineItemType;
  title: string;
  status: TimelineItemStatus;
  timestamp: string;
  duration?: number; // in seconds
  expanded?: boolean;
}

/**
 * Phase represents a major workflow stage (Research, Content Generation, etc.)
 */
export interface PhaseItem extends TimelineItem {
  type: 'phase';
  description?: string;
  progress?: number; // 0-100
  agentCount?: number;
  toolCount?: number;
}

/**
 * Agent represents an AI agent working on a task
 */
export interface AgentItem extends TimelineItem {
  type: 'agent';
  role: string;
  reasoning?: string;
  output?: string;
  phaseId?: string; // Parent phase
}

/**
 * Tool represents a tool/function being used
 */
export interface ToolItem extends TimelineItem {
  type: 'tool';
  toolName: string;
  input?: string;
  output?: string;
  error?: string;
  agentId?: string; // Parent agent
}

/**
 * Timeline state container
 */
export interface TimelineState {
  items: TimelineItem[];
  currentPhase: string | null;
  overallProgress: number;
  startTime: string;
  endTime?: string;
}

/**
 * Helper type guards
 */
export function isPhaseItem(item: TimelineItem): item is PhaseItem {
  return item.type === 'phase';
}

export function isAgentItem(item: TimelineItem): item is AgentItem {
  return item.type === 'agent';
}

export function isToolItem(item: TimelineItem): item is ToolItem {
  return item.type === 'tool';
}
