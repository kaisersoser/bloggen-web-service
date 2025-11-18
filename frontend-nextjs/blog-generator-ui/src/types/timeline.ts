/**
 * Timeline Visualization Types
 * 
 * Simplified data structures for linear workflow visualization
 * Alternative to complex graph structures used by React Flow
 */

export type TimelineItemType = 'phase' | 'agent' | 'tool' | 'connection';
export type TimelineItemStatus = 'pending' | 'in_progress' | 'completed' | 'error' | 'connected' | 'disconnected';

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
  children?: TimelineItem[]; // Nested items (tools under agents, reasoning steps, etc.)
}

/**
 * Phase represents a major workflow stage (Research, Content Generation, etc.)
 * Displayed horizontally on main timeline
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
 * Displayed horizontally on main timeline with vertical children (tools, reasoning)
 */
export interface AgentItem extends TimelineItem {
  type: 'agent';
  role: string;
  reasoning?: string;
  output?: string;
  phaseId?: string; // Parent phase
  children?: ToolItem[]; // Tools used by this agent (displayed vertically)
}

/**
 * Tool represents a tool/function being used
 * Displayed vertically under parent agent
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
 * Connection event (start/end of stream)
 * Displayed horizontally on main timeline
 */
export interface ConnectionItem extends TimelineItem {
  type: 'connection';
  connectionType: 'start' | 'end';
  message?: string;
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
  isComplete?: boolean; // Flag to prevent clearing timeline
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

export function isConnectionItem(item: TimelineItem): item is ConnectionItem {
  return item.type === 'connection';
}
