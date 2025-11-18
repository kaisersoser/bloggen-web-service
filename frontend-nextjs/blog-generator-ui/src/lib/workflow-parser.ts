/**
 * Workflow Graph Builder
 * 
 * Transforms SSE events from the backend into a visual workflow graph structure.
 * This class maintains the graph state and incrementally updates it as new events arrive.
 * 
 * Key responsibilities:
 * - Parse SSE events into graph nodes and edges
 * - Maintain parent-child relationships (phase → agent → tool)
 * - Track active nodes for UI highlighting
 * - Generate unique IDs for nodes and edges
 * 
 * Usage:
 * ```typescript
 * const builder = new WorkflowGraphBuilder({ taskId: 'task-123' });
 * 
 * // Subscribe to SSE events
 * useEnhancedSSEConnection(taskId, (event) => {
 *   const updatedGraph = builder.processSSEEvent(event);
 *   setGraph(updatedGraph);
 * });
 * ```
 */

import type {
  WorkflowGraph,
  WorkflowNode,
  WorkflowEdge,
  SSEEvent,
  SSEEventData,
  GraphBuilderState,
  GraphBuilderConfig,
} from '@/types/workflow-graph';

export class WorkflowGraphBuilder {
  private graph: WorkflowGraph;
  private state: GraphBuilderState;
  private config: GraphBuilderConfig;

  constructor(config: GraphBuilderConfig) {
    this.config = {
      enableDebugLogging: false,
      deduplicateNodes: true,
      maxNodes: 100,
      ...config,
    };

    this.graph = {
      nodes: [],
      edges: [],
      activeNodeId: null,
      currentPhase: '',
      overallProgress: 0,
      taskId: config.taskId,
      startTime: new Date().toISOString(),
    };

    this.state = {
      nodeMap: new Map(),
      phaseNodes: new Map(),
      agentNodes: new Map(),
      toolNodes: new Map(),
      currentPhaseId: null,
      currentAgentId: null,
      edgeCounter: 0,
    };

    this.log('WorkflowGraphBuilder initialized', { taskId: config.taskId });
  }

  /**
   * Main entry point: process an SSE event and return updated graph
   */
  processSSEEvent(event: SSEEvent): WorkflowGraph {
    console.log('🎬 [GraphBuilder] ===== Processing SSE Event =====');
    console.log('🎬 [GraphBuilder] Event Type:', event.type);
    console.log('🎬 [GraphBuilder] Event Data:', JSON.stringify(event.data, null, 2));
    console.log('🎬 [GraphBuilder] Current Graph State:', {
      nodeCount: this.state.nodeMap.size,
      edgeCount: this.graph.edges.length,
      currentPhase: this.state.currentPhaseId
    });

    let result: WorkflowGraph;

    switch (event.type) {
      case 'status':
        console.log('➡️ [GraphBuilder] Routing to handleStatusEvent');
        result = this.handleStatusEvent(event.data);
        break;
      case 'agent_thinking':
        console.log('➡️ [GraphBuilder] Routing to handleAgentThinkingEvent');
        result = this.handleAgentThinkingEvent(event.data);
        break;
      case 'tool_usage':
        console.log('➡️ [GraphBuilder] Routing to handleToolUsageEvent');
        result = this.handleToolUsageEvent(event.data);
        break;
      case 'content_stream':
        console.log('➡️ [GraphBuilder] Routing to handleContentStreamEvent');
        result = this.handleContentStreamEvent(event.data);
        break;
      case 'error':
        console.log('➡️ [GraphBuilder] Routing to handleErrorEvent');
        result = this.handleErrorEvent(event.data);
        break;
      default:
        console.log('⚠️ [GraphBuilder] Unknown event type, returning current graph');
        result = this.getGraph();
    }

    console.log('✅ [GraphBuilder] After processing:', {
      nodeCount: this.state.nodeMap.size,
      edgeCount: this.graph.edges.length,
      nodesArray: Array.from(this.state.nodeMap.keys())
    });
    console.log('🎬 [GraphBuilder] ===== Event Processing Complete =====\n');

    return result;
  }  /**
   * Handle 'status' events - creates/updates phase nodes
   */
  private handleStatusEvent(data: SSEEventData): WorkflowGraph {
    console.log('📊 [handleStatusEvent] Processing status event:', data);
    const { step, message, progress, timestamp } = data;

    // Extract phase information from step (e.g., "Step 2/5" or "Research")
    const phaseInfo = this.parsePhaseInfo(step, message);
    const phaseId = `phase-${phaseInfo.name.toLowerCase().replace(/\s+/g, '-')}`;

    // Check if phase node already exists
    let phaseNode = this.state.nodeMap.get(phaseId);

    if (!phaseNode) {
      // Create new phase node
      phaseNode = {
        id: phaseId,
        type: 'phase',
        label: phaseInfo.name,
        status: 'in_progress',
        progress: progress || 0,
        timestamp,
        metadata: {
          phase: phaseInfo.name,
          stepNumber: phaseInfo.stepNumber,
          totalSteps: phaseInfo.totalSteps,
          timestamp,
          raw: data,
        },
      };

      this.addNode(phaseNode);
      this.state.phaseNodes.set(phaseInfo.name, phaseId);

      // Connect to previous phase if exists
      if (this.state.currentPhaseId && this.state.currentPhaseId !== phaseId) {
        this.addEdge(this.state.currentPhaseId, phaseId);
      }
    } else {
      // Update existing phase node
      phaseNode.status = data.status === 'completed' ? 'completed' : 'in_progress';
      phaseNode.progress = progress || phaseNode.progress;
      phaseNode.timestamp = timestamp;
    }

    // Update graph state
    this.graph.activeNodeId = phaseId;
    this.graph.currentPhase = phaseInfo.name;
    this.graph.overallProgress = progress || 0;
    this.state.currentPhaseId = phaseId;

    this.log('Phase node updated', { phaseId, status: phaseNode.status, progress });
    console.log('✅ [handleStatusEvent] Phase node created/updated:', phaseId);
    
    return this.getGraph();
  }

  /**
   * Handle 'agent_thinking' events - creates/updates agent nodes
   */
  private handleAgentThinkingEvent(data: SSEEventData): WorkflowGraph {
    console.log('🧠 [handleAgentThinkingEvent] Processing agent thinking:', data);
    const { agent_name, reasoning, timestamp } = data;

    if (!agent_name) {
      this.log('Agent thinking event missing agent_name', data);
      console.warn('⚠️ [handleAgentThinkingEvent] Missing agent_name, skipping');
      return this.getGraph();
    }

    // Generate unique agent ID (append counter if multiple instances)
    const agentKey = agent_name.toLowerCase().replace(/\s+/g, '-');
    const existingAgentId = this.state.agentNodes.get(agent_name);
    const agentId = existingAgentId || `agent-${agentKey}-${Date.now()}`;

    let agentNode = this.state.nodeMap.get(agentId);

    if (!agentNode) {
      // Create new agent node
      agentNode = {
        id: agentId,
        type: 'agent',
        label: agent_name,
        status: 'in_progress',
        timestamp,
        metadata: {
          agentName: agent_name,
          reasoning,
          parentNodeId: this.state.currentPhaseId || undefined,
          timestamp,
          raw: data,
        },
      };

      this.addNode(agentNode);
      this.state.agentNodes.set(agent_name, agentId);

      // Connect agent to current phase
      if (this.state.currentPhaseId) {
        this.addEdge(this.state.currentPhaseId, agentId);
      }
    } else {
      // Update existing agent node
      agentNode.status = 'in_progress';
      agentNode.timestamp = timestamp;
      if (reasoning) {
        agentNode.metadata.reasoning = reasoning;
      }
    }

    // Update active node
    this.graph.activeNodeId = agentId;
    this.state.currentAgentId = agentId;

    this.log('Agent node updated', { agentId, agentName: agent_name });
    console.log('✅ [handleAgentThinkingEvent] Agent node created/updated:', agentId);
    
    return this.getGraph();
  }

  /**
   * Handle 'tool_usage' events - creates/updates tool nodes
   */
  private handleToolUsageEvent(data: SSEEventData): WorkflowGraph {
    console.log('🔧 [handleToolUsageEvent] Processing tool usage:', data);
    const { tool_name, tool_status, tool_output, tool_error, timestamp } = data;

    if (!tool_name) {
      this.log('Tool usage event missing tool_name', data);
      console.warn('⚠️ [handleToolUsageEvent] Missing tool_name, skipping');
      return this.getGraph();
    }

    // Generate unique tool ID
    const toolKey = tool_name.toLowerCase().replace(/\s+/g, '-');
    const toolId = `tool-${toolKey}-${Date.now()}`;

    let toolNode = this.state.nodeMap.get(toolId);

    if (!toolNode) {
      // Create new tool node
      toolNode = {
        id: toolId,
        type: 'tool',
        label: tool_name,
        status: tool_status === 'finished' ? 'completed' : tool_status === 'error' ? 'failed' : 'in_progress',
        timestamp,
        metadata: {
          toolName: tool_name,
          toolOutput: tool_output,
          toolError: tool_error,
          parentNodeId: this.state.currentAgentId || undefined,
          timestamp,
          raw: data,
        },
      };

      this.addNode(toolNode);
      this.state.toolNodes.set(tool_name, toolId);

      // Connect tool to current agent
      if (this.state.currentAgentId) {
        this.addEdge(this.state.currentAgentId, toolId);
      }
    } else {
      // Update existing tool node
      toolNode.status = tool_status === 'finished' ? 'completed' : tool_status === 'error' ? 'failed' : 'in_progress';
      toolNode.timestamp = timestamp;
      if (tool_output) {
        toolNode.metadata.toolOutput = tool_output;
      }
      if (tool_error) {
        toolNode.metadata.toolError = tool_error;
      }
    }

    this.log('Tool node updated', { toolId, toolName: tool_name, status: tool_status });
    console.log('✅ [handleToolUsageEvent] Tool node created/updated:', toolId);
    
    return this.getGraph();
  }

  /**
   * Handle 'content_stream' events - stores draft content for preview
   */
  private handleContentStreamEvent(data: SSEEventData): WorkflowGraph {
    console.log('📝 [handleContentStreamEvent] Content stream received');
    // Content streams don't create nodes, but we could store for preview modal
    this.log('Content stream received', { length: data.content?.length });
    return this.getGraph();
  }

  /**
   * Handle 'error' events - marks nodes as failed
   */
  private handleErrorEvent(data: SSEEventData): WorkflowGraph {
    console.log('❌ [handleErrorEvent] Error event received:', data);
    const { error } = data;

    // Mark currently active node as failed
    if (this.graph.activeNodeId) {
      const activeNode = this.state.nodeMap.get(this.graph.activeNodeId);
      if (activeNode) {
        activeNode.status = 'failed';
        this.log('Node marked as failed', { nodeId: this.graph.activeNodeId, error });
        console.log('❌ [handleErrorEvent] Node marked as failed:', this.graph.activeNodeId);
      }
    }
    return this.getGraph();
  }

  /**
   * Parse phase information from step string
   */
  private parsePhaseInfo(step?: string, message?: string): { name: string; stepNumber: number; totalSteps: number } {
    // Try to extract from step string (e.g., "Step 2/5")
    if (step) {
      const stepMatch = step.match(/Step (\d+)\/(\d+)/i);
      if (stepMatch) {
        const stepNumber = parseInt(stepMatch[1], 10);
        const totalSteps = parseInt(stepMatch[2], 10);
        
        // Map step numbers to phase names
        const phaseNames: Record<number, string> = {
          1: 'Initialization',
          2: 'Research',
          3: 'Content Generation',
          4: 'Fact Checking',
          5: 'Finalization',
        };
        
        return {
          name: phaseNames[stepNumber] || step,
          stepNumber,
          totalSteps,
        };
      }
    }

    // Fallback to message as phase name
    return {
      name: message || 'Processing',
      stepNumber: 0,
      totalSteps: 5,
    };
  }

  /**
   * Add a node to the graph
   */
  private addNode(node: WorkflowNode): void {
    // Check max nodes limit
    if (this.graph.nodes.length >= (this.config.maxNodes || 100)) {
      console.warn('Max nodes limit reached, skipping node creation');
      return;
    }

    this.graph.nodes.push(node);
    this.state.nodeMap.set(node.id, node);
    this.log('Node added', { nodeId: node.id, type: node.type });
  }

  /**
   * Add an edge to the graph
   */
  private addEdge(sourceId: string, targetId: string, label?: string): void {
    const edgeId = `edge-${this.state.edgeCounter++}`;
    const edge: WorkflowEdge = {
      id: edgeId,
      source: sourceId,
      target: targetId,
      animated: sourceId === this.graph.activeNodeId,
      label,
      type: 'smoothstep',
    };

    this.graph.edges.push(edge);
    this.log('Edge added', { edgeId, source: sourceId, target: targetId });
  }

  /**
   * Get the complete graph state
   */
  getGraph(): WorkflowGraph {
    return { ...this.graph };
  }

  /**
   * Reset the graph (for new generation)
   */
  reset(): void {
    this.graph = {
      nodes: [],
      edges: [],
      activeNodeId: null,
      currentPhase: '',
      overallProgress: 0,
      taskId: this.config.taskId,
      startTime: new Date().toISOString(),
    };

    this.state = {
      nodeMap: new Map(),
      phaseNodes: new Map(),
      agentNodes: new Map(),
      toolNodes: new Map(),
      currentPhaseId: null,
      currentAgentId: null,
      edgeCounter: 0,
    };

    this.log('Graph reset');
  }

  /**
   * Debug logging
   */
  private log(message: string, data?: any): void {
    if (this.config.enableDebugLogging) {
      console.log(`[WorkflowGraphBuilder] ${message}`, data || '');
    }
  }
}
