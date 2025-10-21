/**
 * Workflow Graph Types for Agent Flow Visualization
 * 
 * These types define the graph structure used to visualize the AI blog generation
 * workflow in real-time. The graph is built incrementally from SSE events emitted
 * by the backend's StatusUpdateManager and BlogEventListener.
 */

/**
 * Node status representing the current state of a workflow element
 */
export type NodeStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

/**
 * Node types in the workflow graph
 * - phase: High-level workflow phase (Research, Content, Fact Check, Finalization)
 * - agent: AI agent performing tasks (Senior Researcher, Content Creator, etc.)
 * - tool: External tool used by agents (Serper Search, Web Scraper, etc.)
 */
export type NodeType = 'phase' | 'agent' | 'tool';

/**
 * Metadata specific to each node type
 */
export interface NodeMetadata {
  // Phase-specific
  phase?: string;           // "Research", "Content Generation", etc.
  stepNumber?: number;      // 1-5 for the current step
  totalSteps?: number;      // Total number of steps (usually 5)
  
  // Agent-specific
  agentName?: string;       // "Senior Researcher", "Content Creator"
  reasoning?: string;       // Agent's current reasoning/thought process
  role?: string;            // Agent's role description
  
  // Tool-specific
  toolName?: string;        // "Serper Search", "Web Scraper", "Unsplash Image"
  toolInput?: string;       // Input/query passed to the tool
  toolOutput?: string;      // Raw output from the tool
  toolError?: string;       // Error message if tool failed
  
  // Common metadata
  timestamp?: string;       // ISO timestamp of when node was created/updated
  parentNodeId?: string;    // ID of parent node (for tools linked to agents)
  raw?: any;               // Raw SSE event data for debugging
}

/**
 * Individual node in the workflow graph
 */
export interface WorkflowNode {
  id: string;                   // Unique identifier (e.g., "phase-research", "agent-researcher-1")
  type: NodeType;               // Node type
  label: string;                // Display label
  status: NodeStatus;           // Current status
  progress?: number;            // Progress percentage (0-100) for phase nodes
  timestamp: string;            // ISO timestamp
  metadata: NodeMetadata;       // Type-specific metadata
  position?: { x: number; y: number };  // Position for ReactFlow (set by layout engine)
}

/**
 * Edge connecting two nodes in the workflow graph
 */
export interface WorkflowEdge {
  id: string;                   // Unique identifier (e.g., "phase-research-to-agent-researcher")
  source: string;               // Source node ID
  target: string;               // Target node ID
  animated?: boolean;           // Whether to show animated flow (for active connections)
  label?: string;               // Optional label for the edge
  type?: string;                // Edge type for ReactFlow (e.g., 'smoothstep')
}

/**
 * Complete workflow graph state
 */
export interface WorkflowGraph {
  nodes: WorkflowNode[];        // All nodes in the graph
  edges: WorkflowEdge[];        // All edges connecting nodes
  activeNodeId: string | null;  // ID of currently active node (highlighted)
  currentPhase: string;         // Current phase name (e.g., "Research")
  overallProgress: number;      // Overall progress percentage (0-100)
  taskId: string;               // Associated task ID from backend
  startTime?: string;           // ISO timestamp when graph started
  endTime?: string;             // ISO timestamp when graph completed
}

/**
 * SSE Event structure (from existing useEnhancedSSEConnection)
 * This matches the actual event structure from our backend
 */
export interface SSEEvent {
  type: 'status' | 'log' | 'agent_thinking' | 'tool_usage' | 'content_stream' | 'error';
  data: SSEEventData;
}

/**
 * SSE Event data payload
 */
export interface SSEEventData {
  task_id: string;
  status: string;
  message: string;
  step?: string;                // "Step 2/5", "Research", etc.
  progress?: number;            // 0-100
  timestamp: string;
  
  // Agent thinking specific
  agent_name?: string;
  reasoning?: string;
  
  // Tool usage specific
  tool_name?: string;
  tool_status?: 'started' | 'finished' | 'error';
  tool_output?: string;
  tool_error?: string;
  
  // Content stream specific
  content?: string;
  draft_version?: number;
  
  // Error specific
  error?: string;
  error_type?: string;
}

/**
 * Graph builder state for tracking node relationships
 */
export interface GraphBuilderState {
  nodeMap: Map<string, WorkflowNode>;      // Quick lookup by node ID
  phaseNodes: Map<string, string>;         // Phase name → node ID
  agentNodes: Map<string, string>;         // Agent name → node ID
  toolNodes: Map<string, string>;          // Tool name → node ID
  currentPhaseId: string | null;           // Current phase node ID
  currentAgentId: string | null;           // Current agent node ID
  edgeCounter: number;                     // Counter for unique edge IDs
}

/**
 * Configuration options for WorkflowGraphBuilder
 */
export interface GraphBuilderConfig {
  taskId: string;                          // Task ID for this workflow
  enableDebugLogging?: boolean;            // Whether to log graph updates
  deduplicateNodes?: boolean;              // Whether to deduplicate nodes with same name
  maxNodes?: number;                       // Maximum nodes to prevent memory issues
}
